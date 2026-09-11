"""Seeded conditional return-path analysis, not a forecast or trade executor."""

from collections.abc import Mapping
from typing import Literal, Self, TypedDict

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike, NDArray
from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, model_validator
from sqlalchemy.orm import Session

JSON_OBJECT = TypeAdapter(dict[str, JsonValue])
JSON_ROWS = TypeAdapter(list[dict[str, JsonValue]])
TEXT = TypeAdapter(str)


class FanPoint(TypedDict):
    date: str
    p05: float
    p25: float
    p50: float
    p75: float
    p95: float


class DistributionBin(TypedDict):
    bin_low: float
    bin_high: float
    count: int


class MonteCarloResult(TypedDict):
    settings: dict[str, JsonValue]
    observations: int
    metrics: dict[str, float]
    fan: list[FanPoint]
    terminal_distribution: list[DistributionBin]
    calculation_version: str
    warnings: list[str]


class ReturnSample(BaseModel):
    model_config = ConfigDict(strict=True)
    end: str
    value: float | str | None


class MetricState(BaseModel):
    state: str


class PerformanceInput(BaseModel):
    summary: dict[str, MetricState]
    series: list[ReturnSample]
    valuation_run_id: str
    source_quality: str


class MonteCarloSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["BOOTSTRAP", "BLOCK_BOOTSTRAP", "NORMAL", "SHUFFLE"] = "BLOCK_BOOTSTRAP"
    paths: int = Field(default=2000, ge=100, le=20000)
    horizon: int = Field(default=252, ge=5, le=1000)
    block_length: int = Field(default=5, ge=1, le=63)
    seed: int = Field(default=3110, ge=0, le=2147483647)
    capital: float = Field(default=100000, ge=100, le=1e9, allow_inf_nan=False)
    drawdown_threshold: float = Field(default=0.2, gt=0, lt=1, allow_inf_nan=False)
    loss_threshold: float = Field(default=0.1, ge=0, lt=1, allow_inf_nan=False)
    ruin_fraction: float = Field(default=0.5, gt=0, lt=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def bounded_memory(self) -> Self:
        if self.paths * self.horizon > 5_000_000:
            raise ValueError("Monte Carlo is bounded to five million path steps")
        return self


def monte_carlo(returns: ArrayLike, settings: MonteCarloSettings) -> MonteCarloResult:
    observed = np.asarray(returns, dtype=float)
    if (
        observed.ndim != 1
        or not 60 <= len(observed) <= 5000
        or not np.isfinite(observed).all()
        or (observed <= -1).any()
    ):
        raise ValueError("Monte Carlo needs 60 to 5,000 finite complete returns greater than -100%")
    rng = np.random.default_rng(settings.seed)
    shape = (settings.paths, settings.horizon)
    if settings.method == "NORMAL":
        samples = rng.normal(observed.mean(), observed.std(ddof=1), size=shape)
    elif settings.method == "BOOTSTRAP":
        samples = rng.choice(observed, size=shape)
    elif settings.method == "SHUFFLE":
        if settings.horizon > len(observed):
            raise ValueError("Shuffle horizon cannot exceed observed return count")
        samples = np.array(
            [rng.permutation(observed)[: settings.horizon] for _ in range(settings.paths)]
        )
    else:
        length = min(settings.block_length, len(observed))
        starts = rng.integers(
            0,
            len(observed) - length + 1,
            size=(settings.paths, int(np.ceil(settings.horizon / length))),
        )
        indices = (starts[..., None] + np.arange(length)).reshape(settings.paths, -1)[
            :, : settings.horizon
        ]
        samples = observed[indices]
    clipped = int((samples < -1).sum())
    wealth = np.concatenate(
        [np.ones((settings.paths, 1)), np.cumprod(1 + samples.clip(min=-1), axis=1)], axis=1
    )
    if not np.isfinite(wealth).all():
        raise ValueError("Simulated wealth exceeds finite numerical bounds")
    peaks = np.maximum.accumulate(wealth, axis=1)
    drawdowns = (wealth / peaks - 1).min(axis=1)
    terminal = wealth[:, -1] - 1
    quantiles = np.quantile(wealth * settings.capital, [0.05, 0.25, 0.5, 0.75, 0.95], axis=0)
    loss_probability = float(np.mean(terminal <= -settings.loss_threshold))
    return {
        "settings": settings.model_dump(),
        "observations": len(observed),
        "metrics": {
            "median_return": float(np.median(terminal)),
            "return_p05": float(np.quantile(terminal, 0.05)),
            "return_p95": float(np.quantile(terminal, 0.95)),
            "loss_probability": loss_probability,
            "loss_probability_mc_se": float(
                np.sqrt(loss_probability * (1 - loss_probability) / settings.paths)
            ),
            "drawdown_probability": float(np.mean(drawdowns <= -settings.drawdown_threshold)),
            "ruin_probability": float(np.mean(wealth.min(axis=1) <= settings.ruin_fraction)),
            "median_drawdown": float(np.median(drawdowns)),
            "drawdown_p05": float(np.quantile(drawdowns, 0.05)),
        },
        "fan": [
            {
                "date": str(i),
                "p05": float(quantiles[0, i]),
                "p25": float(quantiles[1, i]),
                "p50": float(quantiles[2, i]),
                "p75": float(quantiles[3, i]),
                "p95": float(quantiles[4, i]),
            }
            for i in range(settings.horizon + 1)
        ],
        "terminal_distribution": [
            {"bin_low": float(lo), "bin_high": float(hi), "count": int(count)}
            for count, lo, hi in zip(*_histogram(terminal), strict=True)
        ],
        "calculation_version": "knk-monte-carlo-1.0 / numpy",
        "warnings": [
            "Conditional resampling analysis, not a forecast. Historical sample selection and regime change can dominate these results.",
            "Block bootstrap preserves dependence only within sampled contiguous blocks. Normal mode is independent and assumes finite normal returns; shuffle preserves only the sampled multiset.",
            "Input returns retain their original cost basis. No additional trading, financing or rebalancing model is inferred.",
            f"Limited-liability floor applied to {clipped} simulated return observations below -100%. Ruin means reaching the configured fraction of starting wealth, not a legal insolvency estimate.",
            "Probability Monte Carlo standard error measures simulation noise only, not estimation or model uncertainty.",
        ],
    }


def _histogram(
    values: NDArray[np.float64],
) -> tuple[NDArray[np.intp], NDArray[np.float64], NDArray[np.float64]]:
    counts, edges = np.histogram(values, bins=30)
    return counts, edges[:-1], edges[1:]


def pin_monte_carlo(session: Session, params: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    from . import models
    from .performance_domain.contracts import PerformanceSettings
    from .portfolio_performance import PortfolioPerformanceService

    settings = MonteCarloSettings.model_validate(params.get("settings", {}))
    values: NDArray[np.float64]
    evidence: dict[str, JsonValue]
    if params.get("backtest_run_id"):
        run = session.get(
            models.AnalysisRun, TEXT.validate_python(params["backtest_run_id"], strict=True)
        )
        if not run or run.kind != "backtest" or run.status != "SUCCEEDED" or not run.result:
            raise ValueError("A completed backtest is required")
        curve = pd.DataFrame(JSON_ROWS.validate_python(run.result["equity_curve"], strict=True))
        if not {"date", "equity"} <= set(curve):
            raise ValueError("Saved backtest requires dated equity observations")
        dates = pd.DatetimeIndex(pd.to_datetime(curve.date, errors="raise"))
        if dates.hasnans or not dates.is_unique or not dates.is_monotonic_increasing:
            raise ValueError("Saved backtest dates must be valid, unique and chronological")
        values = np.asarray(
            pd.to_numeric(curve.equity, errors="raise").pct_change(fill_method=None).iloc[1:],
            dtype=float,
        )
        evidence = {
            "backtest_run_id": run.id,
            "source": run.result["source"],
            "quality": run.result["quality"],
            "as_of": run.result["as_of"],
            "cost_basis": "Saved strategy net curve",
        }
    else:
        report = PerformanceInput.model_validate(
            PortfolioPerformanceService(session).calculate(
                TEXT.validate_python(params.get("portfolio", "KNK_MAIN"), strict=True),
                PerformanceSettings(),
                TEXT.validate_python(params["valuation_run_id"], strict=True)
                if params.get("valuation_run_id") is not None
                else None,
            )
        )
        if report.summary["volatility"].state != "AVAILABLE":
            raise ValueError("Portfolio history is not eligible for statistical analysis")
        values = np.asarray(
            [
                float(row.value) if row.value is not None else np.nan
                for row in report.series
                if pd.Timestamp(row.end).weekday() < 5
            ],
            dtype=float,
        )
        evidence = {
            "valuation_run_id": report.valuation_run_id,
            "source": "Pinned internal portfolio returns",
            "quality": report.source_quality,
            "as_of": report.series[-1].end if report.series else None,
            "cost_basis": "NET ledger returns",
        }
    values = np.asarray(values, dtype=float)
    if not 60 <= len(values) <= 5000 or not np.isfinite(values).all() or (values <= -1).any():
        raise ValueError("Monte Carlo requires at least sixty complete eligible daily returns")
    return {
        **params,
        "settings": settings.model_dump(),
        "_returns": values.tolist(),
        "_evidence": evidence,
    }


def monte_carlo_result(params: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    returns = TypeAdapter(list[float]).validate_python(params["_returns"], strict=True)
    evidence = JSON_OBJECT.validate_python(params["_evidence"], strict=True)
    result = monte_carlo(returns, MonteCarloSettings.model_validate(params["settings"]))
    return JSON_OBJECT.validate_python({**result, **evidence, "inputs": evidence}, strict=True)
