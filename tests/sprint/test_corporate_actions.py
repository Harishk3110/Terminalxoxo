"""Corporate action basis transfers, fractional holdings and rejection atomicity."""

from dataclasses import replace
from datetime import date
from decimal import Decimal as D

import pytest
from app.portfolio_domain.ledger import LedgerState
from app.portfolio_domain.money import ONE, ZERO
from app.portfolio_domain.types import AccountingPolicy, CostMethod, Entry
from hypothesis import given
from hypothesis import strategies as st

DAY = date(2026, 3, 2)


def parent_position(*, short: bool = False) -> LedgerState:
    state = LedgerState(policy=AccountingPolicy(CostMethod.FIFO))
    state.apply(
        Entry(
            "open",
            DAY,
            "SHORT" if short else "BUY",
            "USD",
            D("10"),
            D("100"),
            fx=D("1.3"),
            instrument_id="PARENT",
        )
    )
    return state


def action(kind: str, quantity: str = "0") -> Entry:
    return Entry(
        "action", DAY, kind, "USD", quantity=D(quantity), fx=D("1.4"), instrument_id="PARENT"
    )


@pytest.mark.parametrize("short", [False, True])
def test_split_multiplies_quantity_without_cash_or_basis_changes(short: bool) -> None:
    state = parent_position(short=short)
    original = state.lots["PARENT"]
    native, base, cash = original.cost_native, original.cost_base, state.cash.copy()
    state.apply(replace(action("SPLIT"), metadata={"ratio": "4"}))
    assert state.lots["PARENT"].quantity == (D("-40") if short else D("40"))
    assert state.lots["PARENT"].cost_native == native
    assert state.lots["PARENT"].cost_base == base
    assert state.cash == cash
    assert not state.cost_basis.matches


def test_reverse_split_keeps_fractional_shares_without_synthetic_cash() -> None:
    state = parent_position()
    state.apply(replace(action("REVERSE_SPLIT"), metadata={"ratio": "0.125"}))
    position = state.lots["PARENT"]
    assert position.quantity == D("1.25")
    assert position.cost_native == D("1000")
    assert position.cost_base == D("1300")
    assert state.cash["USD"] == D("-1000")


@pytest.mark.parametrize("ratio", ["0", "-1", "1", "2", "NaN", "Infinity"])
def test_invalid_reverse_split_is_atomic(ratio: str) -> None:
    state = parent_position()
    with pytest.raises(ValueError):
        state.apply(replace(action("REVERSE_SPLIT"), metadata={"ratio": ratio}))
    assert state.lots["PARENT"].quantity == D("10")
    assert state.lots["PARENT"].cost_base == D("1300")


def test_spinoff_conserves_historical_base_basis_and_parent_acquisition_date() -> None:
    state = parent_position()
    entry = replace(
        action("SPINOFF", "2.5"),
        metadata={"child_instrument_id": "CHILD", "cost_allocation": "0.2"},
    )
    state.apply(entry)
    parent, child = state.lots["PARENT"], state.lots["CHILD"]
    assert parent.quantity == D("10")
    assert child.quantity == D("2.5")
    assert child.cost_native == D("200")
    assert child.cost_base == D("260")
    assert parent.cost_base == D("1040")
    assert child.cost_base + parent.cost_base == D("1300")
    assert state.cost_basis.lots_for("CHILD")[0].opened == DAY
    assert state.cost_basis.lots_for("CHILD")[0].entry_id == "action"
    assert state.cash["USD"] == D("-1000")
    assert parent.realised == child.realised == ZERO


def test_zero_cost_spinoff_has_known_zero_basis_not_missing_basis() -> None:
    state = parent_position()
    state.apply(
        replace(
            action("SPINOFF", "3"),
            metadata={"child_instrument_id": "CHILD", "cost_allocation": "0"},
        )
    )
    assert state.lots["CHILD"].quantity == D("3")
    assert state.lots["CHILD"].cost_base == ZERO
    assert state.lots["PARENT"].cost_base == D("1300")


@pytest.mark.parametrize("allocation", ["-0.1", "1", "2", "NaN", "Infinity"])
def test_invalid_spinoff_allocation_leaves_no_child(allocation: str) -> None:
    state = parent_position()
    with pytest.raises(ValueError):
        state.apply(
            replace(
                action("SPINOFF", "2"),
                metadata={"child_instrument_id": "CHILD", "cost_allocation": allocation},
            )
        )
    assert "CHILD" not in state.lots
    assert not state.cost_basis.lots_for("CHILD")
    assert state.lots["PARENT"].cost_base == D("1300")


def test_spinoff_does_not_net_against_short_child() -> None:
    state = parent_position()
    state.apply(Entry("child-short", DAY, "SHORT", "USD", ONE, D("20"), instrument_id="CHILD"))
    with pytest.raises(ValueError, match="short child"):
        state.apply(
            replace(
                action("SPINOFF", "2"),
                metadata={"child_instrument_id": "CHILD", "cost_allocation": "0.2"},
            )
        )
    assert state.lots["PARENT"].cost_base == D("1300")
    assert state.lots["CHILD"].quantity == -ONE


def test_stock_merger_rolls_historical_basis_to_successor() -> None:
    state = parent_position()
    state.apply(
        replace(
            action("MERGER"), metadata={"child_instrument_id": "SUCCESSOR", "exchange_ratio": "1.5"}
        )
    )
    assert state.lots["PARENT"].quantity == ZERO
    assert state.lots["PARENT"].cost_base == ZERO
    assert state.lots["SUCCESSOR"].quantity == D("15")
    assert state.lots["SUCCESSOR"].cost_native == D("1000")
    assert state.lots["SUCCESSOR"].cost_base == D("1300")
    assert state.lots["PARENT"].realised == ZERO
    assert state.cash["USD"] == D("-1000")


def test_merger_cash_boot_uses_explicit_allocated_basis_and_event_fx() -> None:
    state = parent_position()
    state.apply(
        replace(
            action("MERGER"),
            metadata={
                "child_instrument_id": "SUCCESSOR",
                "exchange_ratio": "0.5",
                "cash_per_share": "30",
                "cash_cost_allocation": "0.2",
            },
        )
    )
    assert state.lots["SUCCESSOR"].quantity == D("5")
    assert state.lots["SUCCESSOR"].cost_native == D("800")
    assert state.lots["SUCCESSOR"].cost_base == D("1040")
    assert state.lots["PARENT"].realised == D("160")
    assert state.cash["USD"] == D("-700")
    match = state.cost_basis.matches[0]
    assert match.base_basis == D("260")
    assert match.base_proceeds == D("420")
    assert match.realised_native == D("100")
    assert match.closing_entry_id == "action"


def test_stock_only_merger_cannot_remove_basis_to_nonexistent_cash() -> None:
    state = parent_position()
    with pytest.raises(ValueError, match="stock-only"):
        state.apply(
            replace(
                action("MERGER"),
                metadata={
                    "child_instrument_id": "SUCCESSOR",
                    "exchange_ratio": "1",
                    "cash_cost_allocation": "0.5",
                },
            )
        )
    assert state.lots["PARENT"].quantity == D("10")
    assert not state.cost_basis.matches


@pytest.mark.parametrize("kind", ["SPINOFF", "MERGER"])
def test_short_parent_actions_require_explicit_supported_treatment(kind: str) -> None:
    state = parent_position(short=True)
    with pytest.raises(ValueError, match="long parent"):
        state.apply(
            replace(
                action(kind, "2"), metadata={"child_instrument_id": "CHILD", "exchange_ratio": "1"}
            )
        )
    assert state.lots["PARENT"].quantity == D("-10")


@pytest.mark.parametrize("kind", ["SPINOFF", "MERGER"])
def test_parent_cannot_be_its_own_successor(kind: str) -> None:
    state = parent_position()
    with pytest.raises(ValueError, match="distinct"):
        state.apply(
            replace(
                action(kind, "2"), metadata={"child_instrument_id": "PARENT", "exchange_ratio": "1"}
            )
        )
    assert state.lots["PARENT"].cost_base == D("1300")


@given(
    ratio=st.decimals(
        min_value="0.01", max_value="100", places=2, allow_nan=False, allow_infinity=False
    )
)
def test_split_preserves_total_cost_and_matched_basis_on_full_disposal(ratio: D) -> None:
    state = parent_position()
    state.apply(replace(action("SPLIT"), metadata={"ratio": str(ratio)}))
    quantity = D("10") * ratio
    state.apply(Entry("close", DAY, "SELL", "USD", quantity, D("100"), instrument_id="PARENT"))
    assert state.lots["PARENT"].cost_base == ZERO
    assert state.lots["PARENT"].quantity == ZERO
    assert sum(match.base_basis for match in state.cost_basis.matches) == D("1300")
