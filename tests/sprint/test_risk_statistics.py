from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import SupportsFloat

import numpy as np
import pandas as pd
import pytest
from app.risk_statistics import RiskSettings, calculate_risk, finite


def inputs() -> tuple[pd.DataFrame, pd.Series[float]]:
    rng = np.random.default_rng(17)
    returns = rng.normal(0.0003, 0.01, (100, 2))
    prices = pd.DataFrame(
        100 * np.cumprod(1 + returns, axis=0),
        columns=["A", "B"],
        index=pd.bdate_range("2026-01-01", periods=100),
    )
    prices["SPY"] = prices["A"]
    return prices, pd.Series({"A": 0.4, "B": -0.2})


def required(value: float | None) -> float:
    assert value is not None
    return value


def test_risk_models_are_repeatable_and_components_reconcile() -> None:
    prices, weights = inputs()
    first = calculate_risk(prices, weights, 100000, "SPY")
    second = calculate_risk(prices, weights, 100000, "SPY")
    assert first == second
    assert first.evidence["state"] == "AVAILABLE"
    assert first.metrics["gross_exposure"] == pytest.approx(0.6)
    assert first.metrics["net_exposure"] == pytest.approx(0.2)
    assert first.metrics["hhi"] == pytest.approx(0.2)
    assert sum(
        required(row["risk_contribution"]) for row in first.positions.values()
    ) == pytest.approx(1)
    assert sum(
        required(row["component_volatility"]) for row in first.positions.values()
    ) == pytest.approx(required(first.metrics["volatility"]))
    assert sum(
        required(row["beta_contribution"]) for row in first.positions.values()
    ) == pytest.approx(required(first.metrics["beta"]))
    assert required(first.metrics["cvar_95"]) <= required(first.metrics["var_95"]) <= 0
    assert required(first.metrics["var_99"]) <= required(first.metrics["var_95"])
    assert first.metrics["monte_carlo_var_95"] == pytest.approx(
        required(first.metrics["parametric_var_95"]), rel=0.05
    )
    assert first.evidence["rolling_beta"][-1]["beta"] is not None


@pytest.mark.parametrize("failure", ["missing", "gap", "zero", "negative", "short", "nav"])
def test_incomplete_histories_do_not_become_valid_risk(failure: str) -> None:
    prices, weights = inputs()
    nav: float | None = 100000
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
    assert required(result.metrics["volatility"]) > 0
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


def test_risk_evidence_retains_settings_and_partial_history_schema() -> None:
    prices, weights = inputs()
    settings = RiskSettings(
        minimum_observations=40, ewma_decay=0.9, simulations=1500, seed=0, rolling_window=30
    )
    result = calculate_risk(prices.iloc[:30], weights, 100000, "SPY", settings)
    assert result.evidence["settings"] == settings.model_dump()
    assert list(result.evidence["settings"]) == list(settings.model_dump())
    assert list(result.evidence) == [
        "state",
        "reason",
        "symbols",
        "values",
        "covariance",
        "rolling_beta",
        "settings",
        "version",
        "horizon",
        "annual_periods",
        "methodology",
    ]
    assert result.evidence["symbols"] == ["A", "B"]
    assert result.evidence["values"] == [[None, None], [None, None]]
    assert result.evidence["covariance"] == []
    assert result.evidence["rolling_beta"] == []
    assert result.metrics["observations"] == 29
    for row in result.positions.values():
        assert list(row) == [
            "beta",
            "beta_contribution",
            "risk_contribution",
            "marginal_volatility",
            "component_volatility",
        ]
        assert all(value is None for value in row.values())


def test_existing_numeric_security_labels_are_not_coerced_in_matrix_evidence() -> None:
    prices, _ = inputs()
    prices = prices.rename(columns={"A": 1, "B": 2})
    result = calculate_risk(prices, pd.Series({1: 0.4, 2: -0.2}), 100000, "SPY")
    assert result.evidence["state"] == "AVAILABLE"
    assert result.evidence["symbols"] == [1, 2]
    assert all(isinstance(value, int) for value in result.evidence["symbols"])
    assert list(result.positions) == ["1", "2"]
    assert result.metrics["beta"] is not None


@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        (float("nan"), None),
        (float("inf"), None),
        (Decimal("-0"), -0.0),
        (np.float64(0.25), 0.25),
        ("-1.25", -1.25),
        (b"2.5", 2.5),
        (bytearray(b"3.5"), 3.5),
    ],
)
def test_finite_risk_values_retain_existing_numeric_representations(
    value: SupportsFloat | str | bytes | bytearray | None, expected: float | None
) -> None:
    assert finite(value) == expected
