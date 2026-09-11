from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from app.alpha_statistics import AlphaSettings, alpha_analysis, finite, regression


def sample() -> tuple[pd.Series[float], pd.DataFrame]:
    rng = np.random.default_rng(3110)
    dates = pd.bdate_range("2024-01-01", periods=200)
    factors = pd.DataFrame(
        {"market": rng.normal(0, 0.01, 200), "size": rng.normal(0, 0.008, 200)}, index=dates
    )
    returns = 0.001 + 1.2 * factors.market - 0.3 * factors["size"] + rng.normal(0, 0.001, 200)
    return returns, factors


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        (math.nan, None),
        (math.inf, None),
        (-math.inf, None),
        (0.0, 0.0),
        (-0.0, -0.0),
        (-2.3, -2.3),
    ],
)
def test_finite_alpha_fields_preserve_zero_and_reject_nonfinite_values(
    value: float | None, expected: float | None
) -> None:
    result = finite(value)
    assert result == expected
    if result is not None and expected is not None:
        assert math.copysign(1, result) == math.copysign(1, expected)


def test_hac_regression_recovers_alpha_betas_and_intervals() -> None:
    returns, factors = sample()
    result = regression(returns, factors, AlphaSettings())
    assert result["state"] == "AVAILABLE"
    assert result["alpha_per_period"] is not None
    assert result["confidence_interval"] is not None
    assert result["confidence_interval"][0] is not None
    assert result["confidence_interval"][1] is not None
    assert result["p_value"] is not None and result["r_squared"] is not None
    assert result["alpha_per_period"] == pytest.approx(0.001, abs=0.0002)
    assert result["annualised_alpha"] == pytest.approx(result["alpha_per_period"] * 252)
    assert result["coefficients"][1]["coefficient"] == pytest.approx(1.2, abs=0.04)
    assert result["coefficients"][2]["coefficient"] == pytest.approx(-0.3, abs=0.04)
    assert (
        result["confidence_interval"][0]
        < result["alpha_per_period"]
        < result["confidence_interval"][1]
    )
    assert result["p_value"] < 0.05 and result["r_squared"] > 0.9


def test_rolling_alpha_does_not_see_future_and_excess_is_separate() -> None:
    returns, factors = sample()
    first = alpha_analysis(returns, factors, AlphaSettings(), benchmark=factors.market)
    changed = returns.copy()
    changed.iloc[160:] += 0.5
    second = alpha_analysis(changed, factors, AlphaSettings(), benchmark=factors.market)
    assert first["rolling"][:100] == second["rolling"][:100]
    assert first["raw_cumulative_excess_return"] != first["annualised_alpha"]


@pytest.mark.parametrize("fault", ["short", "missing", "collinear"])
def test_regression_unavailable_states(fault: str) -> None:
    returns, factors = sample()
    if fault == "short":
        returns, factors = returns.iloc[:20], factors.iloc[:20]
    if fault == "missing":
        factors.iloc[0, 0] = np.nan
    if fault == "collinear":
        factors["size"] = factors["market"] * 2
    result = regression(returns, factors, AlphaSettings())
    assert result["state"] == "INSUFFICIENT_DATA"
    assert result["annualised_alpha"] is None and result["reason"]


def test_unaligned_factor_dates_rejected() -> None:
    returns, factors = sample()
    with pytest.raises(ValueError, match="aligned"):
        regression(returns, factors.iloc[::-1], AlphaSettings())


def test_empty_returns_never_report_zero_excess_performance() -> None:
    dates = pd.DatetimeIndex([])
    empty = pd.Series([], index=dates, dtype=float)
    result = alpha_analysis(
        empty, pd.DataFrame({"market": empty}), AlphaSettings(), benchmark=empty
    )
    assert result["state"] == "INSUFFICIENT_DATA"
    assert result["raw_cumulative_excess_return"] is None
