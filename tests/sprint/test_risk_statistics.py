from datetime import date

import numpy as np
import pandas as pd
import pytest
from app.risk_statistics import RiskSettings, calculate_risk


def inputs():
    rng = np.random.default_rng(17)
    returns = rng.normal(0.0003, 0.01, (100, 2))
    prices = pd.DataFrame(
        100 * np.cumprod(1 + returns, axis=0),
        columns=["A", "B"],
        index=pd.bdate_range("2026-01-01", periods=100),
    )
    prices["SPY"] = prices["A"]
    return prices, pd.Series({"A": 0.4, "B": -0.2})


def test_risk_models_are_repeatable_and_components_reconcile() -> None:
    prices, weights = inputs()
    first = calculate_risk(prices, weights, 100000, "SPY")
    second = calculate_risk(prices, weights, 100000, "SPY")
    assert first == second
    assert first.evidence["state"] == "AVAILABLE"
    assert first.metrics["gross_exposure"] == pytest.approx(0.6)
    assert first.metrics["net_exposure"] == pytest.approx(0.2)
    assert first.metrics["hhi"] == pytest.approx(0.2)
    assert sum(row["risk_contribution"] for row in first.positions.values()) == pytest.approx(1)
    assert sum(row["component_volatility"] for row in first.positions.values()) == pytest.approx(
        first.metrics["volatility"]
    )
    assert sum(row["beta_contribution"] for row in first.positions.values()) == pytest.approx(
        first.metrics["beta"]
    )
    assert first.metrics["cvar_95"] <= first.metrics["var_95"] <= 0
    assert first.metrics["var_99"] <= first.metrics["var_95"]
    assert first.metrics["monte_carlo_var_95"] == pytest.approx(
        first.metrics["parametric_var_95"], rel=0.05
    )
    assert first.evidence["rolling_beta"][-1]["beta"] is not None


@pytest.mark.parametrize("failure", ["missing", "gap", "zero", "negative", "short", "nav"])
def test_incomplete_histories_do_not_become_valid_risk(failure):
    prices, weights = inputs()
    nav = 100000
    if failure == "missing":
        prices.iloc[10, 0] = np.nan
    if failure == "gap":
        prices = prices.drop(prices.index[10])
    if failure == "zero":
        prices.iloc[10, 0] = 0
    if failure == "negative":
        prices.iloc[10, 0] = -1
    if failure == "short":
        prices = prices.iloc[:60]
    if failure == "nav":
        nav = None
    result = calculate_risk(prices, weights, nav, "SPY")
    assert result.evidence["state"] == "INSUFFICIENT_DATA"
    assert result.evidence["reason"]
    assert result.metrics["volatility"] is None


def test_missing_benchmark_preserves_security_risk_but_not_beta() -> None:
    prices, weights = inputs()
    prices.loc[prices.index[10], "SPY"] = np.nan
    result = calculate_risk(prices, weights, 100000, "SPY")
    assert result.metrics["volatility"] > 0
    assert result.metrics["beta"] is None


def test_constant_returns_have_zero_volatility_without_fake_beta() -> None:
    prices = pd.DataFrame({"A": [100.0] * 100}, index=pd.bdate_range(date(2026, 1, 1), periods=100))
    result = calculate_risk(prices, pd.Series({"A": 1.0}), 100000, "A")
    assert result.metrics["volatility"] == 0
    assert result.metrics["var_95"] == 0
    assert result.metrics["beta"] is None
    assert result.positions["A"]["risk_contribution"] is None


def test_settings_do_not_allow_unbounded_work_or_nonfinite_estimation() -> None:
    with pytest.raises(ValueError):
        RiskSettings(simulations=100000000)
    with pytest.raises(ValueError):
        RiskSettings(ewma_decay=float("nan"))
