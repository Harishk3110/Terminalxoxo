"""Measured cross-sectional factor diagnostics with explicit IS/OOS separation."""

import math
from typing import Literal, TypedDict

import numpy as np
import pandas as pd
from numpy.typing import NDArray

TECHNICAL_FACTORS = ("MOMENTUM", "REVERSAL", "VOLATILITY", "BETA", "TREND", "DISTANCE_MA")


class FactorObservation(TypedDict):
    date: str
    ic: float
    pearson_ic: float | None
    coverage: int
    coverage_fraction: float
    turnover: float


class QuantileReturn(TypedDict):
    date: str
    q1: float
    q2: float
    q3: float
    q4: float
    q5: float
    spread: float
    estimated_entry_cost: float
    spread_after_entry_cost: float


class FactorSummary(TypedDict):
    observations: int
    mean_ic: float | None
    ic_volatility: float | None
    mean_pearson_ic: float | None
    positive_ic_fraction: float | None
    mean_turnover: float | None
    ic_ir: float | None
    start: str | None
    end: str | None


class FactorDiagnostics(TypedDict):
    lookback: int
    factor: str
    forward_horizon: int
    cost_bps: float
    ic: list[FactorObservation]
    quantile_returns: list[QuantileReturn]
    in_sample: FactorSummary
    out_of_sample: FactorSummary
    state: Literal["CALCULATED", "INSUFFICIENT DATA"]
    warnings: list[str]


def factor_signals(
    frame: pd.DataFrame,
    lookback: int = 21,
    factor: str = "MOMENTUM",
    benchmark: str | None = None,
) -> pd.DataFrame:
    returns = frame.pct_change(fill_method=None)
    if factor == "MOMENTUM":
        return frame / frame.shift(lookback) - 1
    if factor == "REVERSAL":
        return -(frame / frame.shift(5) - 1)
    if factor == "VOLATILITY":
        return returns.rolling(lookback).std() * float(np.sqrt(252))
    if factor == "DISTANCE_MA":
        return frame / frame.rolling(lookback).mean() - 1
    if factor == "TREND":
        return (frame / frame.shift(lookback) - 1) / (
            returns.rolling(lookback).std() * float(np.sqrt(lookback))
        ).replace(0, np.nan)
    if factor == "BETA":
        if benchmark is None or benchmark not in frame:
            return frame * np.nan
        return (
            returns.rolling(lookback)
            .cov(returns[benchmark])
            .div(returns[benchmark].rolling(lookback).var().replace(0, np.nan), axis=0)
        )
    return frame * np.nan


def factor_statistics(
    frame: pd.DataFrame,
    lookback: int = 21,
    horizon: int = 5,
    factor: str = "MOMENTUM",
    benchmark: str | None = None,
    cost_bps: float = 10,
) -> FactorDiagnostics:
    if not 2 <= lookback <= 500 or not 1 <= horizon <= 63:
        raise ValueError("Invalid factor lookback or forward horizon")
    if (
        not 0 <= cost_bps <= 500
        or not frame.index.is_unique
        or not frame.index.is_monotonic_increasing
    ):
        raise ValueError("Invalid costs or factor date grid")
    signals = factor_signals(frame, lookback, factor, benchmark)
    forward = frame.shift(-horizon) / frame - 1
    # Rank the same pairwise-observed cross sections once, rather than rebuilding
    # and sorting pandas objects for every day in every interactive request.
    observed = signals.notna() & forward.notna()
    signal_ranks = signals.where(observed).rank(axis=1).to_numpy()
    forward_ranks = forward.where(observed).rank(axis=1).to_numpy()
    signal_values = signals.to_numpy()
    forward_values = forward.to_numpy()
    masks = observed.to_numpy()
    observations: list[FactorObservation] = []
    quantiles: list[QuantileReturn] = []
    previous_weights: NDArray[np.float64] | None = None
    for offset, day in enumerate(frame.index):
        mask = masks[offset]
        signal = signal_values[offset, mask]
        returns = forward_values[offset, mask]
        coverage = len(signal)
        if coverage < 5 or len(np.unique(signal)) < 2 or len(np.unique(returns)) < 2:
            continue
        ic = float(np.corrcoef(signal_ranks[offset, mask], forward_ranks[offset, mask])[0, 1])
        if not math.isfinite(ic):
            continue
        order = np.argsort(signal, kind="stable")
        groups = np.array_split(order, 5)
        values = [float(returns[index].mean()) for index in groups]
        pearson = float(np.corrcoef(signal, returns)[0, 1])
        weights = np.zeros(len(frame.columns))
        columns = np.flatnonzero(mask)
        weights[columns[groups[-1]]] = 1 / len(groups[-1])
        weights[columns[groups[0]]] = -1 / len(groups[0])
        turnover = float(
            np.abs(weights - (previous_weights if previous_weights is not None else 0)).sum()
        )
        previous_weights = weights
        observations.append(
            {
                "date": day.date().isoformat(),
                "ic": ic,
                "pearson_ic": pearson if math.isfinite(pearson) else None,
                "coverage": coverage,
                "coverage_fraction": coverage / len(frame.columns),
                "turnover": turnover,
            }
        )
        quantiles.append(
            {
                "date": day.date().isoformat(),
                "q1": values[0],
                "q2": values[1],
                "q3": values[2],
                "q4": values[3],
                "q5": values[4],
                "spread": values[-1] - values[0],
                "estimated_entry_cost": 2 * cost_bps / 10000,
                "spread_after_entry_cost": values[-1] - values[0] - 2 * cost_bps / 10000,
            }
        )
    cutoff = int(len(observations) * 0.7)

    def summary(rows: list[FactorObservation]) -> FactorSummary:
        values = pd.Series([r["ic"] for r in rows], dtype=float)
        std = float(values.std()) if len(values) > 1 else None
        return {
            "observations": len(rows),
            "mean_ic": float(values.mean()) if len(values) >= 10 else None,
            "ic_volatility": std,
            "mean_pearson_ic": float(
                pd.Series([row["pearson_ic"] for row in rows], dtype=float).mean()
            )
            if len(rows) >= 10
            else None,
            "positive_ic_fraction": float((values > 0).mean()) if len(rows) >= 10 else None,
            "mean_turnover": float(np.mean([row["turnover"] for row in rows])) if rows else None,
            "ic_ir": float(values.mean()) / std if len(values) >= 10 and std else None,
            "start": rows[0]["date"] if rows else None,
            "end": rows[-1]["date"] if rows else None,
        }

    insample, oos = observations[:cutoff], observations[cutoff:]
    # Purge the forward-return horizon at the split to prevent training labels overlapping OOS.
    insample = insample[:-horizon] if len(insample) > horizon else []
    return {
        "lookback": lookback,
        "factor": factor,
        "forward_horizon": horizon,
        "cost_bps": cost_bps,
        "ic": observations,
        "quantile_returns": quantiles,
        "in_sample": summary(insample),
        "out_of_sample": summary(oos),
        "state": "CALCULATED" if len(insample) >= 10 and len(oos) >= 10 else "INSUFFICIENT DATA",
        "warnings": [
            "Retrospective cross-sectional rank/Pearson IC; fixed 70/30 chronological split with a forward-horizon purge. No model fitting or parameter selection is performed.",
            "Forward-return windows overlap; IC IR is not a significance test. Quantile returns are forward holding-period observations, not a compounded strategy NAV.",
            "Entry-cost sensitivity charges two equal-notional legs once; exits, drift, financing and market impact are excluded. Turnover measures changes in target long/short membership, not realised executed turnover.",
            "Higher quantile means higher raw factor, not necessarily a favourable return prediction. Point-in-time fundamental factors require timestamped historical fundamentals; current snapshots are not backfilled.",
            "A research statistic is not a validated investment edge or paper-trading performance.",
        ],
    }
