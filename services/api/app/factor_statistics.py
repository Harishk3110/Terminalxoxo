"""Measured cross-sectional factor diagnostics with explicit IS/OOS separation."""

import math

import numpy as np
import pandas as pd

TECHNICAL_FACTORS = ("MOMENTUM", "REVERSAL", "VOLATILITY", "BETA", "TREND", "DISTANCE_MA")


def factor_signals(frame, lookback=21, factor="MOMENTUM", benchmark=None):
    returns = frame.pct_change(fill_method=None)
    if factor == "MOMENTUM":
        return frame / frame.shift(lookback) - 1
    if factor == "REVERSAL":
        return -(frame / frame.shift(5) - 1)
    if factor == "VOLATILITY":
        return returns.rolling(lookback).std() * np.sqrt(252)
    if factor == "DISTANCE_MA":
        return frame / frame.rolling(lookback).mean() - 1
    if factor == "TREND":
        return (frame / frame.shift(lookback) - 1) / (
            returns.rolling(lookback).std() * np.sqrt(lookback)
        ).replace(0, np.nan)
    if factor == "BETA":
        if benchmark not in frame:
            return frame * np.nan
        return (
            returns.rolling(lookback)
            .cov(returns[benchmark])
            .div(returns[benchmark].rolling(lookback).var().replace(0, np.nan), axis=0)
        )
    return frame * np.nan


def factor_statistics(
    frame, lookback=21, horizon=5, factor="MOMENTUM", benchmark=None, cost_bps=10
):
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
    observations, quantiles = [], []
    previous_weights = None
    for day in frame.index:
        pairs = pd.DataFrame({"signal": signals.loc[day], "forward": forward.loc[day]}).dropna()
        if len(pairs) < 5 or pairs.signal.nunique() < 2 or pairs.forward.nunique() < 2:
            continue
        ic = float(pairs.signal.rank().corr(pairs.forward.rank()))
        if not math.isfinite(ic):
            continue
        sorted_pairs = pairs.sort_values("signal", kind="stable")
        groups = np.array_split(np.arange(len(sorted_pairs)), 5)
        values = [float(sorted_pairs.iloc[index].forward.mean()) for index in groups]
        pearson = float(pairs.signal.corr(pairs.forward))
        weights = pd.Series(0.0, index=frame.columns)
        weights.loc[sorted_pairs.iloc[groups[-1]].index] = 1 / len(groups[-1])
        weights.loc[sorted_pairs.iloc[groups[0]].index] = -1 / len(groups[0])
        turnover = float(
            (weights - (previous_weights if previous_weights is not None else 0)).abs().sum()
        )
        previous_weights = weights
        observations.append(
            {
                "date": day.date().isoformat(),
                "ic": ic,
                "pearson_ic": pearson if math.isfinite(pearson) else None,
                "coverage": len(pairs),
                "coverage_fraction": len(pairs) / len(frame.columns),
                "turnover": turnover,
            }
        )
        quantiles.append(
            {
                "date": day.date().isoformat(),
                **{f"q{i + 1}": value for i, value in enumerate(values)},
                "spread": values[-1] - values[0],
                "estimated_entry_cost": 2 * cost_bps / 10000,
                "spread_after_entry_cost": values[-1] - values[0] - 2 * cost_bps / 10000,
            }
        )
    cutoff = int(len(observations) * 0.7)

    def summary(rows):
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
