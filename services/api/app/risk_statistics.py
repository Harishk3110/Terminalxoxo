"""Current-weight security risk using aligned returns, NumPy and pandas estimators."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist
from typing import Any, cast

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field


class RiskSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    minimum_observations: int = Field(default=60, ge=20, le=1000, strict=True)
    ewma_decay: float = Field(default=0.94, ge=0.8, le=0.999, allow_inf_nan=False)
    simulations: int = Field(default=10000, ge=1000, le=100000, strict=True)
    seed: int = Field(default=3110, ge=0, le=2147483647, strict=True)
    rolling_window: int = Field(default=60, ge=20, le=1000, strict=True)


@dataclass
class RiskAnalysis:
    metrics: dict[str, float | int | None]
    evidence: dict[str, Any]
    positions: dict[str, dict[str, float | None]]


def finite(value: Any) -> float | None:
    return float(value) if value is not None and math.isfinite(float(value)) else None


def calculate_risk(
    prices: pd.DataFrame,
    weights: pd.Series[float],
    nav: float | None,
    benchmark_id: str | None,
    settings: RiskSettings | None = None,
) -> RiskAnalysis:
    settings = settings or RiskSettings()
    names = list(weights.index)
    weights = weights.astype(float)
    if not np.isfinite(weights.to_numpy()).all():
        raise ValueError("Risk weights must be finite")
    metrics = dict.fromkeys(
        [
            "beta",
            "volatility",
            "ewma_volatility",
            "var_95",
            "var_99",
            "cvar_95",
            "cvar_99",
            "parametric_var_95",
            "parametric_var_99",
            "monte_carlo_var_95",
            "monte_carlo_var_99",
            "monte_carlo_cvar_95",
        ]
    )
    metrics.update(
        {
            "observations": 0,
            "gross_exposure": float(weights.abs().sum()),
            "net_exposure": float(weights.sum()),
            "long_exposure": float(weights.clip(lower=0).sum()),
            "short_exposure": float(-weights.clip(upper=0).sum()),
            "leverage": float(weights.abs().sum()),
            "hhi": float((weights.abs() ** 2).sum()),
            "concentration": float(weights.abs().max()) if len(weights) else 0,
        }
    )
    evidence = {
        "state": "INSUFFICIENT_DATA",
        "reason": None,
        "symbols": names,
        "values": [[None for _ in names] for _ in names],
        "covariance": [],
        "rolling_beta": [],
        "settings": settings.model_dump(),
        "version": "knk-risk-1.0",
        "horizon": "1 trading day",
        "annual_periods": 252,
        "methodology": "Current signed security weights; sample covariance ddof=1; historical linear quantiles; normal parametric and seeded normal-return Monte Carlo; pandas bias-corrected EWMA variance. Cash-FX, liability and nonlinear option risk excluded. Negative values are P&L losses, not positive loss amounts.",
    }
    contributions = {
        str(key): dict.fromkeys(
            [
                "beta",
                "beta_contribution",
                "risk_contribution",
                "marginal_volatility",
                "component_volatility",
            ]
        )
        for key in names
    }
    result = RiskAnalysis(metrics, evidence, contributions)
    if nav is None or not math.isfinite(nav) or nav <= 0 or not names:
        evidence["reason"] = "Positive complete NAV and security positions are required"
        return result
    if not prices.index.is_unique or not prices.index.is_monotonic_increasing:
        raise ValueError("Risk price dates must be unique and ascending")
    prices = prices.loc[[day.weekday() < 5 for day in prices.index]]
    assets = prices.reindex(columns=names)
    if (
        assets.empty
        or assets.isna().any().any()
        or not np.isfinite(assets.to_numpy()).all()
        or (assets <= 0).any().any()
    ):
        evidence["reason"] = "Complete positive marked security histories are required"
        return result
    if any(
        len(pd.bdate_range(previous, current, inclusive="right")) != 1
        for previous, current in zip(assets.index, assets.index[1:], strict=False)
    ):
        evidence["reason"] = (
            "Irregular valuation intervals cannot be treated as daily risk observations"
        )
        return result
    returns = assets.pct_change(fill_method=None).iloc[1:]
    metrics["observations"] = len(returns)
    if len(returns) < settings.minimum_observations:
        evidence["reason"] = (
            f"Requires {settings.minimum_observations} complete daily return observations"
        )
        return result
    covariance = returns.cov()
    correlation = returns.corr()
    portfolio_returns = cast("pd.Series[float]", returns @ weights)
    weight_array = weights.to_numpy(dtype=float)
    variance = float(weight_array @ covariance.to_numpy(dtype=float) @ weight_array)
    deviation = math.sqrt(max(0, variance))
    mean = float(portfolio_returns.mean())
    marginal = covariance @ weights * 252
    volatility = deviation * math.sqrt(252)
    metrics["volatility"] = volatility
    ewma = (
        portfolio_returns.ewm(
            alpha=1 - settings.ewma_decay, adjust=True, min_periods=settings.minimum_observations
        )
        .var(bias=False)
        .iloc[-1]
    )
    metrics["ewma_volatility"] = math.sqrt(float(ewma) * 252) if finite(ewma) is not None else None
    draws = np.random.default_rng(settings.seed).normal(mean, deviation, settings.simulations)
    for confidence in (95, 99):
        probability = (100 - confidence) / 100
        threshold = float(portfolio_returns.quantile(probability, interpolation="linear"))
        tail = portfolio_returns[portfolio_returns <= threshold]
        metrics[f"var_{confidence}"] = min(0, threshold * nav)
        metrics[f"cvar_{confidence}"] = min(0, float(tail.mean()) * nav)
        metrics[f"parametric_var_{confidence}"] = min(
            0, (mean + NormalDist().inv_cdf(probability) * deviation) * nav
        )
        simulated = float(np.quantile(draws, probability))
        metrics[f"monte_carlo_var_{confidence}"] = min(0, simulated * nav)
        if confidence == 95:
            metrics["monte_carlo_cvar_95"] = min(0, float(draws[draws <= simulated].mean()) * nav)
    benchmark = (
        prices[[benchmark_id]].pct_change(fill_method=None)[benchmark_id].iloc[1:]
        if benchmark_id in prices
        else None
    )
    benchmark_valid = (
        benchmark is not None and benchmark.notna().all() and np.isfinite(benchmark).all()
    )
    benchmark_variance = (
        float(np.var(benchmark.to_numpy(dtype=float), ddof=1))
        if benchmark_valid and benchmark is not None
        else 0
    )
    if benchmark_variance > 0 and benchmark is not None:
        metrics["beta"] = float(portfolio_returns.cov(benchmark) / benchmark_variance)
        beta_series = portfolio_returns.rolling(settings.rolling_window).cov(
            benchmark
        ) / benchmark.rolling(settings.rolling_window).var(ddof=1)
        evidence["rolling_beta"] = [
            {"date": str(day), "beta": finite(value)} for day, value in beta_series.items()
        ]
    for key in names:
        beta = (
            float(returns[key].cov(benchmark) / benchmark_variance)
            if benchmark_variance > 0
            else None
        )
        contributions[str(key)] = {
            "beta": beta,
            "beta_contribution": float(weights[key]) * beta if beta is not None else None,
            "risk_contribution": float(weights[key] * marginal[key] / (variance * 252))
            if variance > 0
            else None,
            "marginal_volatility": float(marginal[key] / volatility) if volatility > 0 else None,
            "component_volatility": float(weights[key] * marginal[key] / volatility)
            if volatility > 0
            else None,
        }
    evidence.update(
        {
            "state": "AVAILABLE",
            "values": [[finite(value) for value in row] for row in correlation.values],
            "covariance": [[finite(value) for value in row] for row in covariance.values],
            "start": str(returns.index[0]),
            "end": str(returns.index[-1]),
            "benchmark_state": "AVAILABLE" if benchmark_variance > 0 else "INSUFFICIENT_DATA",
        }
    )
    return result
