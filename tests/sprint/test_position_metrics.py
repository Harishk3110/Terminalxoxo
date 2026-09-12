"""Independent signed-value examples and price/FX decomposition invariants."""

from dataclasses import replace
from decimal import Decimal as D

import pytest
from app.portfolio_domain.position_metrics import (
    ExposurePosition,
    PortfolioPositionService,
    position_exposures,
)
from app.portfolio_domain.types import Lot
from hypothesis import given
from hypothesis import strategies as st


def holding() -> Lot:
    return Lot(
        quantity=D(10),
        cost_native=D(1000),
        cost_base=D(1300),
        realised=D(50),
        income=D(10),
        charges=D(7),
        capitalized_charges=D(2),
    )


def test_long_position_separates_native_and_base_values_and_price_fx_effects() -> None:
    result = PortfolioPositionService.measure(holding(), D(120), D("1.4"))
    assert result.direction == "LONG"
    assert result.native_value == D(1200)
    assert result.base_value == D(1680)
    assert result.unrealised_native == D(200)
    assert result.unrealised_base == D(380)
    assert result.price_pnl_base == D(280)
    assert result.fx_pnl_base == D(100)
    assert result.expensed_charges == D(5)
    assert result.total_pnl == D(435)
    payload = result.payload()
    assert payload["average_cost"] == D(100)
    assert payload["cost_basis_native"] == D(1000)
    assert payload["market_value_base_exact"] == D(1680)
    assert payload["valuation_state"] == "AVAILABLE"
    assert payload["valuation_warnings"] == []


def test_short_liability_has_signed_market_value_and_opposite_fx_sensitivity() -> None:
    lot = replace(holding(), quantity=D(-10), cost_native=D(-1000), cost_base=D(-1300))
    result = PortfolioPositionService.measure(lot, D(90), D("1.4"))
    assert result.direction == "SHORT"
    assert result.native_value == D(-900)
    assert result.base_value == D(-1260)
    assert result.unrealised_native == D(100)
    assert result.unrealised_base == D(40)
    assert result.price_pnl_base == D(140)
    assert result.fx_pnl_base == D(-100)
    assert result.payload()["average_cost"] == D(100)
    assert result.payload()["return"] == D(40) / D(1300)


def test_contract_multiplier_applies_once_to_market_value_and_unit_cost() -> None:
    lot = Lot(quantity=D(3), multiplier=D(50), cost_native=D(15000), cost_base=D(19500))
    result = PortfolioPositionService.measure(lot, D(110), D("1.4"))
    assert result.native_value == D(16500)
    assert result.base_value == D(23100)
    assert result.price_pnl_base == D(2100)
    assert result.fx_pnl_base == D(1500)
    assert result.payload()["average_cost"] == D(100)


def test_missing_fx_does_not_hide_available_native_values() -> None:
    result = PortfolioPositionService.measure(holding(), D(120), None)
    assert result.native_value == D(1200)
    assert result.unrealised_native == D(200)
    assert result.base_value is None
    assert result.price_pnl_base is None
    assert result.fx_pnl_base is None
    assert result.total_pnl is None
    assert result.payload()["return"] is None
    assert result.payload()["valuation_state"] == "UNAVAILABLE"
    assert result.warnings == ("Position FX is unavailable",)


def test_missing_price_retains_only_the_known_recorded_basis_fx_effect() -> None:
    result = PortfolioPositionService.measure(holding(), None, D("1.4"))
    assert result.native_value is None
    assert result.base_value is None
    assert result.unrealised_base is None
    assert result.price_pnl_base is None
    assert result.fx_pnl_base == D(100)
    assert result.warnings == ("Position price is unavailable",)


def test_closed_position_needs_no_current_quote_to_report_realised_income_and_costs() -> None:
    lot = Lot(realised=D(50), income=D(7), charges=D(3))
    result = PortfolioPositionService.measure(lot, None, None)
    assert result.direction == "CLOSED"
    assert result.native_value == result.base_value == 0
    assert result.price_pnl_base == result.fx_pnl_base == 0
    assert result.total_pnl == 54
    assert result.payload()["average_cost"] is None
    assert result.warnings == ()


def test_zero_price_is_a_writeoff_not_a_missing_quote() -> None:
    result = PortfolioPositionService.measure(holding(), D(0), D("1.4"))
    assert result.base_value == 0
    assert result.unrealised_base == D(-1300)
    assert result.payload()["return"] == -1
    assert result.warnings == ()


def test_base_currency_identity_has_no_fx_component() -> None:
    lot = replace(holding(), cost_base=D(1000))
    result = PortfolioPositionService.measure(lot, D(120), D(1))
    assert result.fx_pnl_base == 0
    assert result.price_pnl_base == result.unrealised_base == D(200)


@pytest.mark.parametrize(
    "price,fx,message",
    [
        (D(-1), D(1), "price"),
        (D("NaN"), D(1), "price"),
        (D("Infinity"), D(1), "price"),
        (D(1), D(0), "FX"),
        (D(1), D(-1), "FX"),
        (D(1), D("NaN"), "FX"),
    ],
)
def test_invalid_marks_cannot_poison_valuation(price: D, fx: D, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PortfolioPositionService.measure(holding(), price, fx)


@pytest.mark.parametrize(
    "changes,message",
    [
        ({"quantity": D("NaN")}, "finite"),
        ({"multiplier": D(0)}, "multiplier"),
        ({"quantity": D(0)}, "closed position"),
    ],
)
def test_invalid_position_balances_are_rejected(changes: dict[str, D], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        PortfolioPositionService.measure(replace(holding(), **changes), D(120), D(1))


@given(
    quantity=st.integers(1, 1000),
    old_price=st.integers(1, 500),
    new_price=st.integers(0, 500),
    old_fx=st.integers(50, 200),
    new_fx=st.integers(50, 200),
    side=st.sampled_from([-1, 1]),
)
def test_unrealised_components_tie_exactly_for_both_sides_and_changing_fx(
    quantity: int, old_price: int, new_price: int, old_fx: int, new_fx: int, side: int
) -> None:
    units = D(quantity * side)
    lot = Lot(
        quantity=units, cost_native=units * old_price, cost_base=units * old_price * D(old_fx) / 100
    )
    result = PortfolioPositionService.measure(lot, D(new_price), D(new_fx) / 100)
    assert result.price_pnl_base is not None
    assert result.fx_pnl_base is not None
    assert result.price_pnl_base + result.fx_pnl_base == result.unrealised_base
    assert result.unrealised_base == units * D(new_price) * D(new_fx) / 100 - lot.cost_base


def test_sector_and_beta_contributions_use_signed_unrounded_market_value() -> None:
    rows = [
        ExposurePosition("AAA", "Technology", D("200.005"), D("1.2")),
        ExposurePosition("BBB", "Technology", D(-100), D(".8")),
        ExposurePosition("CCC", "Financials", D(300), None),
    ]
    result = position_exposures(rows, D(1000))
    assert result["AAA"]["nav_weight"] == D(".200005")
    assert result["AAA"]["sector_weight"] == D(".100005")
    assert result["BBB"]["sector_weight"] == D(".100005")
    assert result["AAA"]["beta_contribution"] == D(".240006")
    assert result["BBB"]["beta_contribution"] == D("-.08")
    assert result["CCC"]["beta_contribution"] is None


def test_incomplete_sector_cannot_be_reported_as_a_partial_total() -> None:
    rows = [
        ExposurePosition("AAA", "Tech", D(100), D(1)),
        ExposurePosition("BBB", "Tech", None, D(1)),
        ExposurePosition("CCC", "Other", D(50), D(1)),
    ]
    result = position_exposures(rows, D(1000))
    assert result["AAA"]["nav_weight"] == D(".1")
    assert result["AAA"]["sector_weight"] is None
    assert result["BBB"]["nav_weight"] is None
    assert result["BBB"]["beta_contribution"] is None
    assert result["CCC"]["sector_weight"] == D(".05")


@pytest.mark.parametrize("nav", [None, D(0)])
def test_zero_or_missing_nav_does_not_invent_zero_exposure_weights(nav: D | None) -> None:
    result = position_exposures([ExposurePosition("AAA", "Tech", D(100), D(1))], nav)
    assert result["AAA"] == {"nav_weight": None, "sector_weight": None, "beta_contribution": None}


def test_exposure_rejects_duplicate_positions_and_nonfinite_inputs() -> None:
    row = ExposurePosition("AAA", "Tech", D(100), D(1))
    with pytest.raises(ValueError, match="unique"):
        position_exposures([row, row], D(1000))
    with pytest.raises(ValueError, match="NAV"):
        position_exposures([row], D("NaN"))
    for invalid in (replace(row, base_value=D("NaN")), replace(row, beta=D("NaN"))):
        with pytest.raises(ValueError, match="marks and beta"):
            position_exposures([invalid], D(1000))
