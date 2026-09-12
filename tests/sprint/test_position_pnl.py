"""Independent period mark/cash examples, including closed holdings and corporate actions."""

from datetime import date
from decimal import Decimal as D
from typing import Any

import pytest
from app.portfolio_domain.ledger import LedgerState
from app.portfolio_domain.position_pnl import PositionPeriodPnl, PositionPnlSession
from app.portfolio_domain.types import AccountingPolicy, Entry
from hypothesis import given
from hypothesis import strategies as st

DAY = date(2026, 1, 6)


def event(identifier: str, kind: str, **fields: Any) -> Entry:
    values = {"id": identifier, "day": DAY, "kind": kind, "currency": "SGD", "fx": D(1), **fields}
    for key in ("quantity", "price", "fx", "amount", "fee", "commission", "tax", "multiplier"):
        if key in values:
            values[key] = D(str(values[key]))
    return Entry(**values)


def period(
    before: list[Entry],
    during: list[Entry],
    opening: dict[str, D | None],
    closing: dict[str, D | None],
    policy: AccountingPolicy | None = None,
) -> dict[str, PositionPeriodPnl]:
    ledger = LedgerState(policy=policy or AccountingPolicy())
    for row in before:
        ledger.apply(row)
    session = PositionPnlSession({key: lot.quantity for key, lot in ledger.lots.items()}, opening)
    first_movement = len(ledger.cash_service.movements)
    for row in during:
        ledger.apply(row)
        session.record(row)
    return session.finish(closing, ledger.cash_service.movements[first_movement:])


def initial() -> Entry:
    return event("opening", "BUY", instrument_id="AAA", quantity="10", price="100")


def test_held_position_gain_comes_from_marks_without_ledger_activity() -> None:
    row = period([initial()], [], {"AAA": D(1000)}, {"AAA": D(1100)})["AAA"]
    assert row.pnl == D(100)
    assert row.economic_cash == row.internal_transfer == row.external_security_flow == 0


@pytest.mark.parametrize(
    "kind,quantity,close,expected",
    [("BUY", "2", "1440", "199"), ("SELL", "3", "840", "199"), ("SELL", "10", "0", "199")],
)
def test_trade_cash_and_fees_are_counted_once(
    kind: str, quantity: str, close: str, expected: str
) -> None:
    row = period(
        [initial()],
        [event("trade", kind, instrument_id="AAA", quantity=quantity, price="120", commission="1")],
        {"AAA": D(1000)},
        {"AAA": D(close)},
    )["AAA"]
    assert row.pnl == D(expected)
    assert row.internal_transfer == 0
    assert row.external_security_flow == 0


def test_short_open_cover_and_remaining_liability_have_correct_signs() -> None:
    short = event("short", "SHORT", instrument_id="AAA", quantity="10", price="100", fee="1")
    opened = period([], [short], {}, {"AAA": D(-900)})["AAA"]
    assert opened.pnl == D(99)
    covered = period(
        [short],
        [event("cover", "COVER", instrument_id="AAA", quantity="4", price="90", fee="1")],
        {"AAA": D(-1000)},
        {"AAA": D(-540)},
    )["AAA"]
    assert covered.pnl == D(99)
    assert covered.economic_cash == D(-361)


@pytest.mark.parametrize("kind", ["DIVIDEND", "INTEREST"])
def test_income_after_full_position_close_is_not_lost(kind: str) -> None:
    closed = event("close", "SELL", instrument_id="AAA", quantity="10", price="100")
    row = period(
        [initial(), closed],
        [event("income", kind, instrument_id="AAA", amount="10", tax="2")],
        {},
        {},
    )["AAA"]
    assert row.opening_value == row.closing_value == 0
    assert row.economic_cash == row.pnl == D(8)


@pytest.mark.parametrize("kind", ["FEE", "COMMISSION", "TAX"])
def test_standalone_position_expense_uses_replayed_cash(kind: str) -> None:
    row = period(
        [initial()],
        [event("expense", kind, instrument_id="AAA", amount="3")],
        {"AAA": D(1000)},
        {"AAA": D(1000)},
    )["AAA"]
    assert row.pnl == D(-3)


def test_security_transfers_are_external_capital_not_investment_gain() -> None:
    incoming = period(
        [],
        [event("in", "TRANSFER_IN", instrument_id="AAA", quantity="10", price="100", fee="2")],
        {},
        {"AAA": D(1000)},
    )["AAA"]
    assert incoming.external_security_flow == D(1000)
    assert incoming.pnl == D(-2)
    outgoing = period(
        [initial()],
        [event("out", "TRANSFER_OUT", instrument_id="AAA", quantity="10", price="110", fee="2")],
        {"AAA": D(1000)},
        {},
    )["AAA"]
    assert outgoing.external_security_flow == D(-1100)
    assert outgoing.pnl == D(98)


@pytest.mark.parametrize("kind,ratio", [("SPLIT", "2"), ("REVERSE_SPLIT", ".5")])
def test_unit_change_without_value_change_has_zero_pnl(kind: str, ratio: str) -> None:
    result = period(
        [initial()],
        [event("split", kind, instrument_id="AAA", metadata={"ratio": ratio})],
        {"AAA": D(1000)},
        {"AAA": D(1000)},
    )
    assert result["AAA"].pnl == 0


def test_spinoff_transfers_comparison_capital_to_successor() -> None:
    result = period(
        [initial()],
        [
            event(
                "spin",
                "SPINOFF",
                instrument_id="AAA",
                quantity="5",
                metadata={"child_instrument_id": "BBB", "cost_allocation": ".2"},
            )
        ],
        {"AAA": D(1000)},
        {"AAA": D(800), "BBB": D(200)},
    )
    assert result["AAA"].internal_transfer == D(-200)
    assert result["BBB"].internal_transfer == D(200)
    assert result["AAA"].pnl == result["BBB"].pnl == 0
    assert "recorded cost-allocation" in result["BBB"].payload()["methodology"]


def test_spinoff_into_an_existing_child_position_retains_its_opening_value() -> None:
    child = event("child", "BUY", instrument_id="BBB", quantity="2", price="50")
    result = period(
        [initial(), child],
        [
            event(
                "spin",
                "SPINOFF",
                instrument_id="AAA",
                quantity="5",
                metadata={"child_instrument_id": "BBB", "cost_allocation": ".2"},
            )
        ],
        {"AAA": D(1000), "BBB": D(100)},
        {"AAA": D(800), "BBB": D(310)},
    )
    assert result["BBB"].opening_value == D(100)
    assert result["BBB"].pnl == D(10)
    assert result["AAA"].pnl == 0


def merger() -> Entry:
    return event(
        "merge",
        "MERGER",
        instrument_id="AAA",
        metadata={
            "child_instrument_id": "BBB",
            "exchange_ratio": "2",
            "cash_per_share": "5",
            "cash_cost_allocation": ".05",
        },
    )


def test_merger_consideration_is_actual_cash_not_zero_transaction_gross() -> None:
    result = period([initial()], [merger()], {"AAA": D(1000)}, {"BBB": D(950)})
    assert result["AAA"].economic_cash == D(50)
    assert result["AAA"].internal_transfer == D(-950)
    assert result["AAA"].pnl == result["BBB"].pnl == 0


def test_partial_sale_before_merger_preserves_realised_daily_gain() -> None:
    sale = event("sale", "SELL", instrument_id="AAA", quantity="2", price="120")
    result = period([initial()], [sale, merger()], {"AAA": D(1000)}, {"BBB": D(760)})
    assert result["AAA"].economic_cash == D(280)
    assert result["AAA"].pnl == D(40)
    assert result["BBB"].pnl == 0


def test_same_day_purchase_is_included_in_stock_merger_reference_value() -> None:
    purchase = event("add", "BUY", instrument_id="AAA", quantity="2", price="120")
    stock = event(
        "stock",
        "MERGER",
        instrument_id="AAA",
        metadata={"child_instrument_id": "BBB", "exchange_ratio": "2"},
    )
    result = period([initial()], [purchase, stock], {"AAA": D(1000)}, {"BBB": D(1240)})
    assert result["BBB"].internal_transfer == D(1240)
    assert result["AAA"].pnl == result["BBB"].pnl == 0


@pytest.mark.parametrize(
    "opening,closing,warning", [(None, D(1100), "Opening"), (D(1000), None, "Closing")]
)
def test_missing_marks_remain_unknown_instead_of_fabricating_gains(
    opening: D | None, closing: D | None, warning: str
) -> None:
    row = period([initial()], [], {"AAA": opening}, {"AAA": closing})["AAA"]
    assert row.pnl is None
    assert row.payload()["state"] == "UNAVAILABLE"
    assert row.payload()["pnl"] is None
    assert any(text.startswith(warning) for text in row.warnings)


def test_missing_parent_mark_propagates_to_both_corporate_action_allocations() -> None:
    result = period([initial()], [merger()], {"AAA": None}, {"BBB": D(950)})
    assert result["AAA"].pnl is None
    assert result["BBB"].pnl is None
    assert result["BBB"].internal_transfer is None
    assert "Corporate transfer reference value is unavailable" in result["BBB"].warnings


def test_unrelated_cash_and_old_movements_do_not_enter_position_pnl() -> None:
    ledger = LedgerState()
    ledger.apply(initial())
    session = PositionPnlSession({"AAA": D(10)}, {"AAA": D(1000)})
    deposit = event("cash", "DEPOSIT", amount="100")
    ledger.apply(deposit)
    session.record(deposit)
    rows = session.finish({"AAA": D(1000)}, ledger.cash_service.movements)
    assert set(rows) == {"AAA"}
    assert rows["AAA"].pnl == rows["AAA"].economic_cash == 0


@given(child_value=st.integers(0, 2000), cash_per_share=st.integers(0, 20))
def test_corporate_transfer_allocation_cannot_create_or_destroy_total_pnl(
    child_value: int, cash_per_share: int
) -> None:
    action = event(
        "action",
        "MERGER",
        instrument_id="AAA",
        metadata={
            "child_instrument_id": "BBB",
            "exchange_ratio": "2",
            "cash_per_share": str(cash_per_share),
            "cash_cost_allocation": ".2" if cash_per_share else "0",
        },
    )
    rows = period([initial()], [action], {"AAA": D(1000)}, {"BBB": D(child_value)})
    transfers, contributions = [], []
    for row in rows.values():
        assert row.internal_transfer is not None
        assert row.pnl is not None
        transfers.append(row.internal_transfer)
        contributions.append(row.pnl)
    assert sum(transfers, D(0)) == 0
    assert sum(contributions, D(0)) == D(child_value + cash_per_share * 10 - 1000)


def test_duplicate_interval_entry_is_rejected() -> None:
    session = PositionPnlSession({}, {})
    session.record(initial())
    with pytest.raises(ValueError, match="duplicate transaction"):
        session.record(initial())
