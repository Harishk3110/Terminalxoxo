"""Subledger classification, settlement and reconciliation independent of storage."""

from dataclasses import replace
from datetime import date
from decimal import Decimal as D

import pytest
from app.portfolio_domain.cash import CashMovement
from app.portfolio_domain.ledger import LedgerState
from app.portfolio_domain.postings import (
    BalanceAdjustment,
    CurrencyMark,
    PostingCategory,
    outstanding_postings,
    summarize_postings,
    transaction_postings,
)
from app.portfolio_domain.types import AccountingPolicy, CostMethod, Entry
from hypothesis import given
from hypothesis import strategies as st

DAY = date(2026, 1, 5)
SETTLE = date(2026, 1, 7)
MARKS = {"USD": CurrencyMark(D("1.4"), {"source": "TEST FX", "as_of": "2026-01-06"})}


@pytest.mark.parametrize(
    "kind,sign", [("DEPOSIT", 1), ("WITHDRAWAL", -1), ("TRANSFER_IN", 1), ("TRANSFER_OUT", -1)]
)
def test_signed_capital_preserves_recorded_fx_and_account(kind: str, sign: int) -> None:
    entry = Entry("flow", DAY, kind, "USD", amount=D("100"), fx=D("1.3"), account_id="acct")
    row = transaction_postings(entry, AccountingPolicy())[0]
    assert row.native_amount == sign * D("100")
    assert row.base_amount == sign * D("130")
    assert row.category == PostingCategory.CAPITAL
    assert row.account_id == "acct"
    assert row.transaction_id == "flow"
    assert row.provenance["basis"] == "RECORDED TRANSACTION FX"


def test_in_kind_transfer_is_capital_but_not_a_cash_settlement() -> None:
    entry = Entry(
        "in-kind",
        DAY,
        "TRANSFER_IN",
        "USD",
        quantity=D("5"),
        price=D("100"),
        fx=D("1.3"),
        instrument_id="AAA",
        settle_date=SETTLE,
    )
    state = LedgerState()
    state.apply(entry)
    posting = transaction_postings(entry, state.policy)[0]
    assert posting.base_amount == state.external_flows == D("650")
    assert posting.instrument_id == "AAA"
    assert outstanding_postings(state.cash_service.movements, [], DAY, MARKS) == []


@pytest.mark.parametrize("kind", ["DIVIDEND", "INTEREST"])
def test_income_and_withholding_are_distinct_components(kind: str) -> None:
    entry = Entry(
        "income", DAY, kind, "USD", amount=D("12"), tax=D("2"), fx=D("1.3"), instrument_id="AAA"
    )
    rows = transaction_postings(entry, AccountingPolicy())
    totals = summarize_postings(rows)
    assert totals["income"] == D("15.6")
    assert totals["taxes"] == D("2.6")
    assert totals["fees_paid"] == 0
    assert len(rows) == 2
    assert rows[0].instrument_id == rows[1].instrument_id == "AAA"


@pytest.mark.parametrize("kind", ["COMMISSION", "FEE", "TAX"])
@pytest.mark.parametrize("via_charges", [False, True])
def test_standalone_expenses_are_consumed_once(kind: str, via_charges: bool) -> None:
    entry = Entry(
        "expense",
        DAY,
        kind,
        "USD",
        amount=D("0") if via_charges else D("5"),
        fee=D("2") if via_charges else D("0"),
        commission=D("3") if via_charges else D("0"),
        fx=D("1.3"),
    )
    policy = AccountingPolicy(capitalize_commissions=True, capitalize_fees=True)
    rows = transaction_postings(entry, policy)
    assert len(rows) == 1
    assert rows[0].base_amount == D("6.5")
    assert rows[0].capitalized_native == 0
    state = LedgerState(policy)
    state.apply(entry)
    totals = summarize_postings(rows)
    assert totals["fees_paid"] == state.fees
    assert totals["taxes"] == state.taxes


@given(
    commission=st.decimals(min_value="0", max_value="40", places=4),
    fee=st.decimals(min_value="0", max_value="40", places=4),
    tax=st.decimals(min_value="0", max_value="40", places=4),
    cap_commission=st.booleans(),
    cap_fee=st.booleans(),
)
def test_posting_totals_reconcile_to_replay_for_every_cost_policy(
    commission: D,
    fee: D,
    tax: D,
    cap_commission: bool,
    cap_fee: bool,
) -> None:
    policy = AccountingPolicy(CostMethod.FIFO, cap_commission, cap_fee)
    entries = [
        Entry("capital", DAY, "DEPOSIT", "USD", amount=D("10000"), fx=D("1.3")),
        Entry(
            "buy",
            DAY,
            "BUY",
            "USD",
            quantity=D("5"),
            price=D("100"),
            instrument_id="AAA",
            commission=commission,
            fee=fee,
            tax=tax,
            fx=D("1.3"),
        ),
    ]
    state = LedgerState(policy)
    for entry in entries:
        state.apply(entry)
    totals = summarize_postings(
        row for entry in entries for row in transaction_postings(entry, policy)
    )
    assert totals["external_flows"] == state.external_flows
    assert totals["capitalized_charges"] == state.capitalized_charges
    assert totals["expensed_fees"] == state.expensed_fees
    assert totals["fees_paid"] == state.fees
    assert totals["taxes"] == state.taxes


def test_sale_charges_retain_provenance_and_policy_treatment() -> None:
    entry = Entry(
        "sale",
        DAY,
        "SELL",
        "USD",
        quantity=D("10"),
        price=D("100"),
        commission=D("3"),
        fee=D("2"),
        tax=D("1"),
        fx=D("1.3"),
        instrument_id="AAA",
        metadata={"fx_source": "USER PROVIDED", "external_reference": "statement-row-9"},
    )
    rows = transaction_postings(entry, AccountingPolicy(capitalize_commissions=True))
    assert {row.kind: row.capitalized_base for row in rows} == {
        "COMMISSION": D("3.9"),
        "FEE": D("0"),
        "TAX": D("0"),
    }
    assert len({row.key for row in rows}) == 3
    assert all(row.provenance["external_reference"] == "statement-row-9" for row in rows)


def test_pending_receivables_and_payables_are_gross_not_offset() -> None:
    movements = [
        CashMovement("buy", "USD", D("-100"), D("1.3"), DAY, SETTLE, "acct", "TRADE"),
        CashMovement("sell", "USD", D("100"), D("1.3"), DAY, SETTLE, "acct", "TRADE"),
    ]
    rows = outstanding_postings(movements, [], DAY, MARKS)
    assert {row.category for row in rows} == {PostingCategory.ACCRUAL, PostingCategory.LIABILITY}
    totals = summarize_postings(rows)
    assert totals["receivables"] == totals["payables"] == D("140")
    assert all(row.fx_rate == D("1.4") for row in rows)
    assert all(row.provenance["basis"] == "PENDING SETTLEMENT" for row in rows)


@pytest.mark.parametrize("as_of", [date(2026, 1, 4), SETTLE, date(2026, 1, 8)])
def test_pending_component_absent_before_trade_and_from_settlement(as_of: date) -> None:
    movement = CashMovement("trade", "USD", D("-100"), D("1.3"), DAY, SETTLE)
    assert outstanding_postings([movement], [], as_of, MARKS) == []


def test_missing_valuation_fx_is_null_not_zero_or_transaction_fx() -> None:
    movement = CashMovement("trade", "JPY", D("-100"), D("0.01"), DAY, SETTLE)
    row = outstanding_postings([movement], [], DAY, MARKS)[0]
    assert row.native_amount == D("100")
    assert row.fx_rate is row.base_amount is None
    assert row.provenance["source"] == "UNAVAILABLE"
    assert summarize_postings([row])["payables"] is None
    assert row.payload()["base_amount"] is None


def test_missing_component_contaminates_only_its_own_total_in_either_order() -> None:
    movements = [
        CashMovement("usd", "USD", D("-100"), D("1.3"), DAY, SETTLE),
        CashMovement("jpy", "JPY", D("-100"), D(".01"), DAY, SETTLE),
    ]
    rows = outstanding_postings(movements, [], DAY, MARKS)
    for ordered in (rows, list(reversed(rows))):
        totals = summarize_postings(ordered)
        assert totals["payables"] is None
        assert totals["receivables"] == D("0")
        assert totals["income"] == D("0")


def test_signed_adjustment_reversals_retain_both_source_rows() -> None:
    original = BalanceAdjustment("first", DAY, "accrued_income", "USD", D("50"), "Original accrual")
    reverse = replace(original, id="reverse", amount=D("-20"), reason="Correct accrual")
    rows = outstanding_postings([], [original, reverse], DAY, MARKS)
    assert len(rows) == 2
    assert summarize_postings(rows)["accrued_income"] == D("42")
    assert {row.adjustment_id for row in rows} == {"first", "reverse"}
    assert all(row.transaction_id is None for row in rows)
    assert rows[1].provenance["reason"] == "Correct accrual"


def test_adjustment_dates_and_categories_are_respected() -> None:
    rows = outstanding_postings(
        [],
        [
            BalanceAdjustment("late", SETTLE, "accrued_income", "USD", D("50"), "Future accrual"),
            BalanceAdjustment("fee", DAY, "accrued_fees", "USD", D("20"), "Unpaid fee"),
        ],
        DAY,
        MARKS,
    )
    assert len(rows) == 1
    assert rows[0].category == PostingCategory.LIABILITY
    assert summarize_postings(rows)["accrued_fees"] == D("28")
    assert summarize_postings(rows)["fees_paid"] == 0


@pytest.mark.parametrize("rate", ["0", "-1", "NaN", "Infinity"])
def test_invalid_currency_mark_rejected(rate: str) -> None:
    with pytest.raises(ValueError):
        CurrencyMark(D(rate), {})


def test_invalid_balance_bucket_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown NAV balance bucket"):
        BalanceAdjustment("bad", DAY, "cash", "USD", D("2"), "Wrong bucket")
