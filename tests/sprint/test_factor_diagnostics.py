import numpy as np
import pandas as pd
import pytest
from app.factor_statistics import TECHNICAL_FACTORS, factor_signals, factor_statistics


def prices():
    rng = np.random.default_rng(31)
    return pd.DataFrame(
        100 * np.exp(np.cumsum(rng.normal(0.001, 0.01, size=(200, 10)), axis=0)),
        index=pd.bdate_range("2024-01-01", periods=200),
        columns=[f"S{i}" for i in range(10)],
    )


@pytest.mark.parametrize("factor", TECHNICAL_FACTORS)
def test_factor_diagnostics_are_measured_and_purged(factor):
    frame = prices()
    data = factor_statistics(frame, 21, 5, factor, "S0", 10)
    assert data["state"] == "CALCULATED"
    assert data["in_sample"]["end"] < data["out_of_sample"]["start"]
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


def test_unknown_fundamental_factor_never_backfills_current_snapshot():
    data = factor_statistics(prices(), 21, 5, "VALUE")
    assert data["state"] == "INSUFFICIENT DATA"
    assert data["ic"] == []
