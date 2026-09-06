"""Cost-basis examples plus independent conservation and provenance checks."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from app.portfolio_domain.cost_basis import CostBasisService
from app.portfolio_domain.ledger import LedgerState
from app.portfolio_domain.money import ONE, ZERO, money
from app.portfolio_domain.types import AccountingPolicy, CostMethod, Direction, Entry, Lot
from hypothesis import given
from hypothesis import strategies as st

DAY = date(2026, 1, 5)


def trade(identifier: str, kind: str, quantity: str, price: str, offset: int = 0) -> Entry:
    return Entry(
        identifier,
        DAY + timedelta(days=offset),
        kind,
        "USD",
        D(quantity),
        D(price),
        instrument_id="AAPL",
    )


def two_lots(method: CostMethod = CostMethod.AVERAGE) -> LedgerState:
    state = LedgerState(policy=AccountingPolicy(method))
    state.apply(trade("open-a", "BUY", "10", "100"))
    state.apply(trade("open-b", "BUY", "20", "130", 1))
    return state


def test_average_matches_proportionally_without_losing_lot_identity() -> None:
    state = two_lots()
    state.apply(trade("close", "SELL", "15", "150", 2))
    position = state.lots["AAPL"]
    assert position.quantity == D("15")
    assert position.cost_native == D("1800")
    assert position.realised == D("450")
    matches = state.cost_basis.matches
    assert [item.quantity for item in matches] == [D("5"), D("10")]
    assert [item.opening_entry_id for item in matches] == ["open-a", "open-b"]
    assert {item.closing_entry_id for item in matches} == {"close"}
    assert sum(item.base_basis for item in matches) == D("1800")
    assert sum(item.base_proceeds for item in matches) == D("2250")


def test_fifo_exhausts_oldest_then_partially_matches_second_lot() -> None:
    state = two_lots(CostMethod.FIFO)
    state.apply(trade("close", "SELL", "15", "150", 2))
    position = state.lots["AAPL"]
    assert position.quantity == D("15")
    assert position.cost_base == D("1950")
    assert position.realised == D("600")
    assert [item.quantity for item in state.cost_basis.matches] == [D("10"), D("5")]
    assert len(state.cost_basis.lots_for("AAPL")) == 1
    assert state.cost_basis.lots_for("AAPL")[0].entry_id == "open-b"


@pytest.mark.parametrize("method", list(CostMethod))
def test_full_sale_clears_every_basis_residual(method: CostMethod) -> None:
    state = two_lots(method)
    state.apply(trade("partial", "SELL", "7.33333333", "141.17", 2))
    remaining = state.lots["AAPL"].quantity
    state.apply(trade("final", "SELL", str(remaining), "145.10", 3))
    assert state.lots["AAPL"].quantity == ZERO
    assert state.lots["AAPL"].cost_native == ZERO
    assert state.lots["AAPL"].cost_base == ZERO
    assert state.cost_basis.lots_for("AAPL") == []
    assert sum(match.quantity for match in state.cost_basis.matches) == D("30")
    assert money(sum(match.native_basis for match in state.cost_basis.matches)) == D("3600")


@pytest.mark.parametrize("method", list(CostMethod))
def test_changing_policy_changes_realised_not_total_economic_pnl(method: CostMethod) -> None:
    state = two_lots(method)
    state.apply(trade("sale", "SELL", "12", "140", 2))
    position = state.lots["AAPL"]
    unrealised = position.quantity * D("142") - position.cost_base
    economic = state.cash["USD"] + position.quantity * D("142")
    assert money(position.realised + unrealised) == money(economic)
    assert economic == D("636")


@pytest.mark.parametrize("capitalize_commissions", [True, False])
@pytest.mark.parametrize("capitalize_fees", [True, False])
def test_opening_charges_follow_policy_tax_always_expensed(
    capitalize_commissions: bool,
    capitalize_fees: bool,
) -> None:
    policy = AccountingPolicy(CostMethod.AVERAGE, capitalize_commissions, capitalize_fees)
    state = LedgerState(policy=policy)
    entry = replace(trade("buy", "BUY", "10", "100"), commission=D("5"), fee=D("2"), tax=D("1"))
    state.apply(entry)
    capitalized = (D("5") if capitalize_commissions else ZERO) + (
        D("2") if capitalize_fees else ZERO
    )
    position = state.lots["AAPL"]
    assert position.cost_base == D("1000") + capitalized
    assert state.cash["USD"] == D("-1008")
    assert position.expensed_charges == D("8") - capitalized
    assert state.expensed_fees == D("7") - capitalized
    assert state.taxes == ONE
    assert position.capitalized_charges == capitalized


def test_capitalized_commissions_on_both_sides_are_not_charged_twice() -> None:
    state = LedgerState(policy=AccountingPolicy(CostMethod.FIFO, True, True))
    state.apply(replace(trade("buy", "BUY", "10", "100"), commission=D("10"), fee=D("2")))
    state.apply(
        replace(trade("sale", "SELL", "10", "120", 1), commission=D("12"), fee=D("3"), tax=D("5"))
    )
    position = state.lots["AAPL"]
    assert position.realised == D("173")
    assert position.expensed_charges == D("5")
    assert position.realised - position.expensed_charges == state.cash["USD"] == D("168")
    assert state.capitalized_charges == D("27")
    assert state.expensed_fees == ZERO


@pytest.mark.parametrize("method,expected", [(CostMethod.AVERAGE, "350"), (CostMethod.FIFO, "400")])
def test_short_cover_cost_and_sign(method: CostMethod, expected: str) -> None:
    state = LedgerState(policy=AccountingPolicy(method))
    state.apply(trade("short-1", "SHORT", "10", "150"))
    state.apply(trade("short-2", "SHORT", "10", "140", 1))
    state.apply(trade("cover", "COVER", "10", "110", 2))
    position = state.lots["AAPL"]
    assert position.quantity == D("-10")
    assert position.realised == D(expected)
    assert position.cost_base < ZERO
    assert state.cash["USD"] == D("1800")
    assert all(match.direction == Direction.SHORT for match in state.cost_basis.matches)


def test_short_capitalization_reduces_opening_proceeds_and_increases_cover_cost() -> None:
    state = LedgerState(policy=AccountingPolicy(CostMethod.FIFO, True, True))
    state.apply(replace(trade("short", "SHORT", "5", "100"), commission=D("4")))
    assert state.lots["AAPL"].cost_native == D("-496")
    state.apply(replace(trade("cover", "COVER", "5", "80", 1), fee=D("3")))
    assert state.lots["AAPL"].realised == D("93")
    assert state.cash["USD"] == D("93")


def test_base_and_native_realised_use_recorded_trade_fx() -> None:
    state = LedgerState()
    state.apply(replace(trade("buy", "BUY", "10", "100"), fx=D("1.30")))
    state.apply(replace(trade("sell", "SELL", "4", "120", 1), fx=D("1.35")))
    match = state.cost_basis.matches[0]
    assert match.native_basis == D("400")
    assert match.base_basis == D("520")
    assert match.native_proceeds == D("480")
    assert match.base_proceeds == D("648")
    assert match.realised_native == D("80")
    assert match.realised_base == D("128")
    assert state.lots["AAPL"].cost_base == D("780")


@pytest.mark.parametrize("kind", ["BUY", "SHORT"])
def test_contract_multiplier_is_applied_to_basis_and_cash(kind: str) -> None:
    state = LedgerState()
    state.apply(replace(trade("open", kind, "2", "4.25"), multiplier=D("100")))
    sign = ONE if kind == "BUY" else -ONE
    assert state.lots["AAPL"].cost_base == sign * D("850")
    assert state.cash["USD"] == -sign * D("850")
    assert state.lots["AAPL"].multiplier == D("100")


@pytest.mark.parametrize(
    "kind,quantity,price",
    [("SELL", "31", "120"), ("SELL", "1", "0"), ("SHORT", "1", "120"), ("COVER", "1", "120")],
)
def test_rejected_security_movement_preserves_state(kind: str, quantity: str, price: str) -> None:
    state = two_lots()
    before = (state.cash.copy(), state.lots["AAPL"].quantity, state.lots["AAPL"].cost_base)
    with pytest.raises(ValueError):
        state.apply(trade("invalid", kind, quantity, price, 2))
    assert (state.cash, state.lots["AAPL"].quantity, state.lots["AAPL"].cost_base) == before
    assert not state.cost_basis.matches
    assert len(state.cost_basis.lots_for("AAPL")) == 2


def test_multiplier_mismatch_does_not_mutate_open_lots() -> None:
    state = two_lots()
    with pytest.raises(ValueError, match="multiplier"):
        state.apply(replace(trade("wrong", "SELL", "1", "120", 2), multiplier=D("100")))
    assert state.lots["AAPL"].quantity == D("30")


def test_lot_ids_are_deterministic_for_same_replay() -> None:
    first, second = two_lots(), two_lots()
    assert [lot.id for lot in first.cost_basis.lots_for("AAPL")] == [
        lot.id for lot in second.cost_basis.lots_for("AAPL")
    ]
    assert len({lot.id for lot in first.cost_basis.lots_for("AAPL")}) == 2


def test_standalone_fifo_orders_acquisition_dates() -> None:
    service = CostBasisService(AccountingPolicy(CostMethod.FIFO))
    service.open_position(trade("new", "BUY", "5", "120", 3), Direction.LONG)
    service.open_position(trade("old", "BUY", "5", "100"), Direction.LONG)
    matches = service.close_position(trade("sale", "SELL", "2", "140", 4), Direction.LONG)
    assert len(matches) == 1
    assert matches[0].opening_entry_id == "old"
    assert matches[0].native_basis == D("200")


def test_rollup_preserves_income_realised_and_charges() -> None:
    service = CostBasisService()
    service.open_position(trade("buy", "BUY", "2", "100"), Direction.LONG)
    position = Lot(realised=D("20"), income=D("5"), charges=D("3"))
    service.rollup("AAPL", position)
    assert (position.realised, position.income, position.charges) == (D("20"), D("5"), D("3"))
    assert position.quantity == D("2")
    assert position.cost_base == D("200")


@given(
    first=st.integers(1, 1000),
    second=st.integers(1, 1000),
    first_price=st.integers(1, 10000),
    second_price=st.integers(1, 10000),
    sale_price=st.integers(1, 10000),
    method=st.sampled_from(list(CostMethod)),
)
def test_round_trip_conserves_cash_and_realised_pnl(
    first: int,
    second: int,
    first_price: int,
    second_price: int,
    sale_price: int,
    method: CostMethod,
) -> None:
    state = LedgerState(policy=AccountingPolicy(method))
    state.apply(trade("first", "BUY", str(first), str(first_price)))
    state.apply(trade("second", "BUY", str(second), str(second_price), 1))
    state.apply(trade("partial", "SELL", str(D(first + second) / 3), str(sale_price), 2))
    remaining = state.lots["AAPL"].quantity
    state.apply(trade("final", "SELL", str(remaining), str(sale_price), 3))
    expected = D((first + second) * sale_price - first * first_price - second * second_price)
    assert money(state.lots["AAPL"].realised) == money(expected)
    assert money(state.cash["USD"]) == money(expected)
    assert state.lots["AAPL"].cost_native == ZERO
    assert state.lots["AAPL"].cost_base == ZERO
    assert money(sum(match.quantity for match in state.cost_basis.matches)) == D(first + second)
