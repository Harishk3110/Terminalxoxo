"""Contract specifications are checked only within the requested observation cut-off."""

import json
from datetime import UTC, date, datetime, time

import pytest
from app.option_contracts import ChainContract
from app.options_analytics import OptionLeg, OptionsRequest, analyse_chain, position_analytics
from app.options_results import ChainAnalysis, PositionAnalysis
from pydantic import TypeAdapter

AT = datetime(2026, 1, 8, 20, tzinfo=UTC)


def chain_row(**changes: object) -> ChainContract:
    return ChainContract.model_validate(
        {
            "symbol": "DATED",
            "option_symbol": "DATED-C100",
            "expiry": date(2026, 2, 8),
            "strike": 100,
            "right": "CALL",
            "multiplier": 100,
            "exercise_style": "EUROPEAN",
            "currency": "SGD",
            "timestamp": AT,
            "iv_unit": "DECIMAL",
            "iv": 0.2,
            "open_interest": 50,
            **changes,
        }
    )


@pytest.mark.parametrize("future_first", [False, True])
def test_future_contract_specification_does_not_change_historical_result(
    future_first: bool,
) -> None:
    historical = chain_row()
    future = chain_row(strike=110, timestamp=datetime(2026, 1, 9, 20, tzinfo=UTC))
    config = OptionsRequest(symbol="DATED")
    expected = analyse_chain([historical], config, 100, AT)
    candidates = [future, historical] if future_first else [historical, future]
    assert analyse_chain(candidates, config, 100, AT) == expected


@pytest.mark.parametrize(
    "change",
    [
        {"strike": 110},
        {"multiplier": 10},
        {"exercise_style": "AMERICAN"},
        {"expiry_time_utc": time(16)},
    ],
)
def test_conflicting_eligible_contract_specifications_are_rejected(
    change: dict[str, object],
) -> None:
    historical = chain_row(timestamp=datetime(2026, 1, 7, 20, tzinfo=UTC))
    conflicting = chain_row(**change)
    with pytest.raises(ValueError, match="conflicting contract specifications"):
        analyse_chain([historical, conflicting], OptionsRequest(symbol="DATED"), 100, AT)


def test_only_future_contracts_are_unavailable() -> None:
    future = chain_row(timestamp=datetime(2026, 1, 9, 20, tzinfo=UTC))
    with pytest.raises(ValueError, match="No matching chain observations"):
        analyse_chain([future], OptionsRequest(symbol="DATED"), 100, AT)


@pytest.mark.parametrize("open_interest", [None, 0, 50])
def test_result_contract_retains_missing_versus_zero_interest(open_interest: int | None) -> None:
    result = analyse_chain(
        [chain_row(open_interest=open_interest)], OptionsRequest(symbol="DATED"), 100, AT
    )
    assert TypeAdapter(ChainAnalysis).validate_python(result, strict=True) == result
    wire = json.loads(json.dumps(result, allow_nan=False))
    assert wire["items"][0]["open_interest"] == open_interest
    if open_interest is None:
        assert wire["items"][0]["gex"] is None
        assert wire["summary"]["net_gex"] is None and wire["coverage"]["gex_included"] == 0
    elif open_interest == 0:
        assert wire["items"][0]["gex"] == 0
        assert wire["summary"]["net_gex"] == 0 and wire["coverage"]["gex_included"] == 1
    else:
        assert wire["items"][0]["gex"] < 0 and wire["coverage"]["gex_included"] == 1


def test_position_contract_preserves_explicit_zero_premium_and_owned_quantity() -> None:
    result = analyse_chain([chain_row()], OptionsRequest(symbol="DATED"), 100, AT)
    report = position_analytics(
        result, [OptionLeg(option_symbol="DATED-C100", quantity=2, premium=0)], equity_quantity=7
    )
    assert TypeAdapter(PositionAnalysis).validate_python(report, strict=True) == report
    assert report["items"][0]["premium"] == 0
    assert next(point["pnl"] for point in report["payoff"] if point["spot"] == 110) == 2070
    assert next(point["pnl"] for point in report["payoff"] if point["spot"] == 90) == -70
    delta = result["items"][0]["delta"]
    assert delta is not None
    assert report["totals"]["delta"] == pytest.approx(delta * 200 + 7)


@pytest.mark.parametrize("quantity", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_equity_quantity_rejected(quantity: float) -> None:
    result = analyse_chain([chain_row()], OptionsRequest(symbol="DATED"), 100, AT)
    with pytest.raises(ValueError, match="Equity quantity must be finite"):
        position_analytics(result, [], equity_quantity=quantity)
