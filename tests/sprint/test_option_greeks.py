import math

import pytest
from app.option_greeks import PricingInputs, greeks, implied_iv


def inputs(**overrides: str | float) -> PricingInputs:
    return PricingInputs.model_validate(
        {
            "right": "CALL",
            "spot": 100,
            "strike": 100,
            "years": 1,
            "risk_free": 0.05,
            "dividend_yield": 0,
            "volatility": 0.2,
            **overrides,
        }
    )


def required(value: float | None) -> float:
    assert value is not None
    return value


def test_known_european_reference_price_and_greeks_units() -> None:
    result = greeks(inputs())
    assert result["theoretical_price"] == pytest.approx(10.450583572185565)
    assert result["delta"] == pytest.approx(0.6368306511756191)
    assert result["gamma"] == pytest.approx(0.018762017345846895)
    assert result["vega"] == pytest.approx(0.3752403469169379)
    assert result["theta"] == pytest.approx(-6.414027546438197 / 365)
    assert result["rho"] == pytest.approx(0.5323248154537634)


def test_put_call_parity_and_implied_volatility_roundtrip() -> None:
    for sigma in (0.05, 0.2, 0.8, 2):
        call, put = (
            inputs(volatility=sigma, dividend_yield=0.02),
            inputs(volatility=sigma, dividend_yield=0.02, right="PUT"),
        )
        c, p = greeks(call), greeks(put)
        assert required(c["theoretical_price"]) - required(p["theoretical_price"]) == pytest.approx(
            100 * math.exp(-0.02) - 100 * math.exp(-0.05)
        )
        assert implied_iv(required(c["theoretical_price"]), call) == pytest.approx(sigma, abs=1e-9)
        assert implied_iv(required(p["theoretical_price"]), put) == pytest.approx(sigma, abs=1e-9)


def test_advanced_sensitivities_against_independent_closed_form_identities() -> None:
    config = inputs()
    result = greeks(config)
    d1 = (math.log(100 / 100) + (0.05 + 0.2**2 / 2)) / 0.2
    d2 = d1 - 0.2
    density = math.exp(-d1 * d1 / 2) / math.sqrt(2 * math.pi)
    assert result["vanna"] == pytest.approx(-density * d2 / 0.2, rel=2e-4)
    assert result["vomma"] == pytest.approx(
        (required(result["vega"]) / 0.01) * d1 * d2 / 0.2, rel=2e-4
    )
    assert result["speed"] == pytest.approx(
        -required(result["gamma"]) / 100 * (d1 / 0.2 + 1), rel=2e-4
    )
    assert result["zomma"] == pytest.approx(
        required(result["gamma"]) * (d1 * d2 - 1) / 0.2, rel=2e-4
    )
    assert all(value is not None and math.isfinite(value) for value in result.values())


@pytest.mark.parametrize(
    "overrides",
    [{"spot": 0}, {"years": 0}, {"volatility": 0}, {"strike": -1}, {"risk_free": float("nan")}],
)
def test_invalid_model_domain(overrides: dict[str, float]) -> None:
    with pytest.raises(ValueError):
        inputs(**overrides)


@pytest.mark.parametrize("price", [0, 100, 101, -1, float("nan")])
def test_out_of_bounds_option_prices_do_not_produce_iv(price: float) -> None:
    with pytest.raises(ValueError):
        implied_iv(price, inputs())
