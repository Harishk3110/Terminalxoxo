from decimal import Decimal as D

import pytest
from app.equity_valuation import (
    DcfRequest,
    DcfScenario,
    DcfScenarioResult,
    WaccInputs,
    calculate_wacc,
    dcf_scenarios,
)
from pydantic import JsonValue, TypeAdapter

BASE: dict[str, JsonValue] = {"year": "2025", "revenue": 100, "debt": 20, "cash": 10, "shares": 10}


def scenario_result(request: DcfRequest, price: int | None = None) -> DcfScenarioResult:
    result = dcf_scenarios(BASE, request, price)
    return TypeAdapter(list[DcfScenarioResult]).validate_python(result["scenarios"])[0]


def test_fcff_uses_change_in_working_capital_and_end_year_discounting() -> None:
    request = DcfRequest(
        symbol="AAA",
        initial_working_capital=D(10),
        scenarios=[
            DcfScenario(
                name="BASE",
                revenue_growth=[D(".1")],
                ebit_margins=[D(".2")],
                tax_rate=D(".25"),
                depreciation_pct=D(".03"),
                capex_pct=D(".05"),
                working_capital_pct=D(".1"),
                terminal_growth=D(0),
            )
        ],
    )
    result = scenario_result(request, 12)
    row = result.forecast[0]
    assert D(row["revenue"]) == 110
    assert D(row["delta_working_capital"]) == 1
    assert D(row["fcff"]) == D("13.3")
    assert float(result.enterprise_value) == pytest.approx(133)
    assert float(result.fair_value) == pytest.approx(12.3)
    assert result.upside is not None and float(result.upside) == pytest.approx(0.025)
    assert len(result.growth_sensitivity) == 25
    assert len(result.exit_sensitivity) == 9


def test_cash_debt_share_overrides_and_negative_equity_are_not_hidden() -> None:
    request = DcfRequest(symbol="AAA", debt_override=D(10000), scenarios=[DcfScenario(name="BEAR")])
    result = scenario_result(request)
    assert result.equity_value < 0
    assert result.upside is None
    assert BASE["debt"] == 20


def test_wacc_uses_market_weights_and_after_tax_debt() -> None:
    result = calculate_wacc(WaccInputs())
    assert D(result["wacc"]) == D(".0719")
    request = DcfRequest(
        symbol="AAA",
        scenarios=[DcfScenario(name="BASE")],
        wacc_inputs=WaccInputs(),
        apply_calculated_wacc=True,
    )
    assert scenario_result(request).assumptions.wacc == D(".0719")


@pytest.mark.parametrize(
    "config",
    [
        {"terminal_growth": ".1"},
        {"revenue_growth": [0]},
        {"wacc": "NaN"},
        {"wacc": 0},
        {"revenue_growth": [-1] * 5},
    ],
)
def test_bad_assumptions_rejected(config: dict[str, JsonValue]) -> None:
    with pytest.raises(ValueError):
        DcfScenario.model_validate({"name": "BASE", **config})


def test_loss_year_has_no_assumed_cash_tax_credit() -> None:
    request = DcfRequest(
        symbol="AAA", scenarios=[DcfScenario(name="BEAR", ebit_margins=[D("-.1")] * 5)]
    )
    assert all(D(row["tax"]) == 0 for row in scenario_result(request).forecast)


def test_exit_multiple_and_missing_baseline() -> None:
    request = DcfRequest(
        symbol="AAA",
        scenarios=[
            DcfScenario(
                name="BASE", terminal_method="EXIT_MULTIPLE", terminal_growth=D(".1"), wacc=D(".05")
            )
        ],
    )
    result = scenario_result(request)
    assert (
        result.terminal_value
        == (result.forecast[-1]["ebit"] + result.forecast[-1]["depreciation"]) * 12
    )
    with pytest.raises(ValueError, match="missing"):
        dcf_scenarios({"revenue": 1}, request)


def test_wire_result_keeps_decimal_strings_and_sensitivity_states() -> None:
    result = dcf_scenarios(BASE, DcfRequest(symbol="AAA", scenarios=[DcfScenario(name="BASE")]))
    scenarios = result["scenarios"]
    assert isinstance(scenarios, list) and isinstance(scenarios[0], dict)
    assert isinstance(scenarios[0]["fair_value"], str)
    sensitivities = scenarios[0]["growth_sensitivity"]
    assert isinstance(sensitivities, list) and isinstance(sensitivities[0], dict)
    assert sensitivities[0]["state"] == "AVAILABLE"
