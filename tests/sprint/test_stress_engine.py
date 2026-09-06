from copy import deepcopy

import pytest
from app.stress_engine import calculate_stress
from app.terminal_analytics import scenario_library


@pytest.fixture
def book():
    return {
        "portfolio": {"nav": 100000, "base_currency": "SGD"},
        "positions": [
            {
                "symbol": "A",
                "sector": "Technology",
                "country": "US",
                "currency": "USD",
                "market_value": 50000,
                "beta": 1.2,
            },
            {
                "symbol": "B",
                "sector": "Financials",
                "country": "US",
                "currency": "SGD",
                "market_value": 20000,
                "beta": 0.5,
            },
        ],
        "cash": [{"currency": "USD", "base_value": 10000}],
        "exposure_balances": [{"currency": "USD", "base_value": -2000, "bucket": "payables"}],
        "source": "test",
        "quality": "DEMO DATA",
        "as_of": "2026-01-01",
        "risk_model": {
            "state": "AVAILABLE",
            "symbols": ["A", "B"],
            "covariance": [[0.0004, 0.0001], [0.0001, 0.0009]],
        },
    }


def test_stress_reconciles_factors_balances_and_beta(book):
    before = deepcopy(book)
    result = calculate_stress(book, {"equity_shock": -10, "fx_shock": 5})
    assert result["loss"] == -4400
    assert sum(row["pnl"] for row in result["contributions"]) == result["loss"]
    assert sum(row["pnl"] for row in result["factor_contributions"]) == result["loss"]
    assert result["beta_after"] == pytest.approx((46200 * 1.2 + 19000 * 0.5) / 95600)
    assert result["hedge_contribution"] is None
    assert book == before


def test_pure_fx_does_not_require_beta(book):
    book["positions"][0]["beta"] = None
    result = calculate_stress(book, {"equity_shock": 0, "fx_shock": 5})
    assert result["loss"] == 2900
    assert result["beta_after"] is None
    with pytest.raises(ValueError, match="beta"):
        calculate_stress(book, {"equity_shock": -5})


def test_correlation_uses_covariance_not_fixed_equity_shock(book):
    scenario = next(row for row in scenario_library() if row["name"] == "Correlation convergence")
    result = calculate_stress(book, scenario)
    base = calculate_stress(book, {**scenario, "correlation_convergence": 0})
    assert result["loss"] < base["loss"] < 0
    assert sum(row["pnl"] for row in result["factor_contributions"]) == result["loss"]
    with pytest.raises(ValueError, match="directional"):
        calculate_stress(book, {**scenario, "equity_shock": -8})
    book["risk_model"]["state"] = "INSUFFICIENT_DATA"
    with pytest.raises(ValueError, match="covariance"):
        calculate_stress(book, scenario)


def test_vix_is_unavailable_not_zero(book):
    result = calculate_stress(book, {"scope": "Volatility"})
    assert result["state"] == "UNAVAILABLE" and result["loss"] is None


@pytest.mark.parametrize(
    "parameters", [{"equity_shock": float("nan")}, {"fx_shock": -100}, {"rates_bp": 1001}]
)
def test_invalid_shocks_rejected(book, parameters):
    with pytest.raises(ValueError):
        calculate_stress(book, parameters)


def test_floor_short_positions_and_tagged_hedges(book):
    book["positions"][0].update(market_value=-50000, beta=3, is_hedge=True)
    result = calculate_stress(book, {"equity_shock": -95})
    assert result["contributions"][0]["post_value"] == 0
    assert result["hedge_contribution"] == 50000
    assert sum(row["pnl"] for row in result["factor_contributions"]) == result["loss"]
