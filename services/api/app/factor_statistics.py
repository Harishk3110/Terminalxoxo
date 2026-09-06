"""Measured cross-sectional factor diagnostics with explicit IS/OOS separation."""
import math
import numpy as np
import pandas as pd


def factor_statistics(frame, lookback=21, horizon=5):
    if not 2 <= lookback <= 500 or not 1 <= horizon <= 63:
        raise ValueError("Invalid factor lookback or forward horizon")
    signals = frame / frame.shift(lookback) - 1
    forward = frame.shift(-horizon) / frame - 1
    observations, quantiles = [], []
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
        observations.append({"date": day.date().isoformat(), "ic": ic, "coverage": len(pairs)})
        quantiles.append({"date": day.date().isoformat(), **{f"q{i + 1}": value for i, value in enumerate(values)}, "spread": values[-1] - values[0]})
    cutoff = int(len(observations) * .7)
    def summary(rows):
        values = pd.Series([r["ic"] for r in rows], dtype=float)
        std = float(values.std()) if len(values) > 1 else None
        return {"observations": len(rows), "mean_ic": float(values.mean()) if len(values) >= 10 else None, "ic_ir": float(values.mean()) / std if len(values) >= 10 and std else None, "start": rows[0]["date"] if rows else None, "end": rows[-1]["date"] if rows else None}
    insample, oos = observations[:cutoff], observations[cutoff:]
    # Purge the forward-return horizon at the split to prevent training labels overlapping OOS.
    insample = insample[:-horizon] if len(insample) > horizon else []
    return {
        "lookback": lookback, "forward_horizon": horizon, "ic": observations, "quantile_returns": quantiles,
        "in_sample": summary(insample), "out_of_sample": summary(oos),
        "state": "CALCULATED" if len(insample) >= 10 and len(oos) >= 10 else "INSUFFICIENT DATA",
        "warnings": ["Retrospective cross-sectional rank IC; fixed 70/30 chronological split with a forward-horizon purge. No model fitting or parameter selection is performed.", "Forward-return windows overlap; IC IR is not a significance test. Quantile returns exclude trading costs, turnover, delistings and financing.", "A research statistic is not a validated investment edge or paper-trading performance."],
    }
