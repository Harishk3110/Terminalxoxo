import numpy as np
import pandas as pd
import pytest
from app.factor_statistics import TECHNICAL_FACTORS, factor_signals, factor_statistics


def prices() -> pd.DataFrame:
    rng = np.random.default_rng(31)
    return pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(0.001, 0.01, size=(200, 10)), axis=0)),
        index=pd.bdate_range("2024-01-01", periods=200),
        columns=[f"S{i}" for i in range(10)],
    )


@pytest.mark.parametrize("factor", TECHNICAL_FACTORS)
def test_factor_diagnostics_are_measured_and_purged(factor: str) -> None:
    frame = prices()
    data = factor_statistics(frame, 21, 5, factor, "S0", 10)
    assert data["state"] == "CALCULATED"
    train_end, test_start = data["in_sample"]["end"], data["out_of_sample"]["start"]
    assert train_end is not None and test_start is not None
    assert train_end < test_start
    assert all(-1.00001 <= row["ic"] <= 1.00001 for row in data["ic"])
    assert all(row["coverage"] == 10 for row in data["ic"])
    assert data["quantile_returns"][0]["spread_after_entry_cost"] == pytest.approx(
        data["quantile_returns"][0]["spread"] - 0.002
    )
    changed = frame.copy()
    changed.iloc[-20:] *= 2
    pd.testing.assert_frame_equal(
        factor_signals(frame, 21, factor, "S0").iloc[:-20],
        factor_signals(changed, 21, factor, "S0").iloc[:-20],
    )


def test_unknown_fundamental_factor_never_backfills_current_snapshot() -> None:
    data = factor_statistics(prices(), 21, 5, "VALUE")
    assert data["state"] == "INSUFFICIENT DATA"
    assert data["ic"] == []


@pytest.mark.parametrize("factor", TECHNICAL_FACTORS)
@pytest.mark.parametrize("missing", [False, True])
def test_factor_cross_sections_match_direct_pandas_calculations(factor: str, missing: bool) -> None:
    frame = prices().iloc[:100].copy()
    if missing:
        frame.iloc[::3, 1:4] = np.nan
        frame.iloc[20:28, :] = 100
    signals = factor_signals(frame, 21, factor, "S0")
    forward = frame.shift(-5) / frame - 1
    result = factor_statistics(frame, 21, 5, factor, "S0", 10)
    previous = pd.Series(0.0, index=frame.columns)
    assert result["ic"]
    assert len(result["ic"]) == len(result["quantile_returns"])
    for row, quantiles in zip(result["ic"], result["quantile_returns"], strict=True):
        day = pd.Timestamp(row["date"])
        pairs = pd.DataFrame({"signal": signals.loc[day], "forward": forward.loc[day]}).dropna()
        assert row["ic"] == float(pairs.signal.rank().corr(pairs.forward.rank()))
        assert row["pearson_ic"] == float(pairs.signal.corr(pairs.forward))
        assert row["coverage"] == len(pairs)
        assert row["coverage_fraction"] == len(pairs) / len(frame.columns)
        ordered = pairs.sort_values("signal", kind="stable")
        buckets = np.array_split(np.arange(len(ordered)), 5)
        values = [
            quantiles["q1"],
            quantiles["q2"],
            quantiles["q3"],
            quantiles["q4"],
            quantiles["q5"],
        ]
        for value, bucket in zip(values, buckets, strict=True):
            assert value == float(ordered.iloc[bucket].forward.mean())
        weights = pd.Series(0.0, index=frame.columns)
        weights.loc[ordered.take(buckets[0]).index] = -1 / len(buckets[0])
        weights.loc[ordered.take(buckets[-1]).index] = 1 / len(buckets[-1])
        assert row["turnover"] == float((weights - previous).abs().sum())
        previous = weights


def test_missing_benchmark_returns_do_not_invent_beta_observations() -> None:
    frame = prices()
    frame.iloc[::3, 0] = np.nan
    result = factor_statistics(frame, 21, 5, "BETA", "S0", 10)
    assert result["state"] == "INSUFFICIENT DATA"
    assert result["ic"] == []
    assert result["quantile_returns"] == []
