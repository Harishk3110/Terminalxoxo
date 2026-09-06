from datetime import UTC, datetime

import pytest
from app.option_contracts import ChainContract, normalize_option
from app.options_analytics import OptionLeg, OptionsRequest, analyse_chain, position_analytics

AS_OF = datetime(2026, 1, 2, 20, tzinfo=UTC)


def contract(**overrides):
    return ChainContract(
        **{
            "symbol": "AAA",
            "option_symbol": "AAA-C-100",
            "expiry": "2026-02-02",
            "strike": 100,
            "right": "CALL",
            "multiplier": 100,
            "exercise_style": "EUROPEAN",
            "currency": "SGD",
            "timestamp": AS_OF,
            "iv_unit": "DECIMAL",
            "iv": 0.2,
            "open_interest": 50,
            "bid": 3,
            "ask": 4,
            **overrides,
        }
    )


def test_gex_formula_dealer_signs_and_open_interest_not_owned_quantity():
    contracts = [contract(), contract(option_symbol="AAA-P-100", right="PUT")]
    for sign in ("DEALER_SHORT", "NEUTRAL", "CALL_POSITIVE_PUT_NEGATIVE"):
        result = analyse_chain(
            contracts, OptionsRequest(symbol="AAA", dealer_sign=sign), 100, AS_OF
        )
        first = result["items"][0]
        expected = 50 * first["gamma"] * 100 * 100**2 * 0.01 * (-1 if sign == "DEALER_SHORT" else 1)
        assert first["gex"] == pytest.approx(expected)
        assert result["summary"]["net_gex"] == pytest.approx(
            sum(row["net_gex"] for row in result["by_strike"])
        )
        assert result["coverage"]["gex_included"] == 2
        if sign == "CALL_POSITIVE_PUT_NEGATIVE":
            assert result["summary"]["net_gex"] == pytest.approx(0)
    positions = position_analytics(result, [OptionLeg(option_symbol="AAA-C-100", quantity=-2)])
    assert positions["totals"]["gamma"] == pytest.approx(-2 * 100 * result["items"][0]["gamma"])
    assert len(positions["payoff"]) == 101


def test_stale_expired_and_missing_oi_not_silently_zero():
    rows = [
        contract(open_interest=None),
        contract(option_symbol="OLD", timestamp=datetime(2025, 1, 1, tzinfo=UTC)),
        contract(option_symbol="EXPIRED", expiry="2025-12-01"),
    ]
    result = analyse_chain(rows, OptionsRequest(symbol="AAA"), 100, AS_OF)
    assert result["summary"]["net_gex"] is None
    assert result["coverage"]["missing_gex"] == 3
    assert result["state"] == "UNAVAILABLE"


def test_provider_units_and_american_approximation_require_consent():
    row = contract(exercise_style="AMERICAN", gamma=0.1, delta=0.5, theta=-0.03, vega=0.2, rho=0.1)
    assert (
        analyse_chain([row], OptionsRequest(symbol="AAA"), 100, AS_OF)["items"][0]["gamma"] is None
    )
    assert (
        analyse_chain(
            [row], OptionsRequest(symbol="AAA", allow_american_approximation=True), 100, AS_OF
        )["items"][0]["state"]
        == "BSM APPROXIMATION"
    )
    assert (
        analyse_chain([row], OptionsRequest(symbol="AAA", greek_source="PROVIDER"), 100, AS_OF)[
            "items"
        ][0]["gamma"]
        is None
    )
    row.greek_units = "STANDARD"
    report = analyse_chain([row], OptionsRequest(symbol="AAA", greek_source="PROVIDER"), 100, AS_OF)
    assert report["items"][0]["gamma"] == 0.1
    assert report["coverage"]["spot_profile_contracts"] == 0


def test_iv_percent_conversion_and_invalid_quotes():
    row = normalize_option(
        contract(iv=0.25).model_dump(mode="json") | {"iv": 25, "iv_unit": "PERCENT"}
    )
    assert ChainContract.model_validate(row).volatility == 0.25
    with pytest.raises(ValueError):
        contract(bid=5, ask=4)
    with pytest.raises(ValueError):
        contract(iv=25)
    with pytest.raises(ValueError):
        contract(timestamp=datetime(2026, 1, 1))


def test_unknown_position_and_mixed_expiry_payoff_unavailable():
    rows = [contract(), contract(option_symbol="LATER", expiry="2026-03-02")]
    result = analyse_chain(rows, OptionsRequest(symbol="AAA"), 100, AS_OF)
    report = position_analytics(result, [OptionLeg(option_symbol="MISSING", quantity=2)])
    assert report["state"] == "PARTIAL_DATA" and report["totals"]["gamma"] is None
    report = position_analytics(
        result,
        [
            OptionLeg(option_symbol="AAA-C-100", quantity=1),
            OptionLeg(option_symbol="LATER", quantity=-1),
        ],
    )
    assert report["payoff_state"] == "UNAVAILABLE"
