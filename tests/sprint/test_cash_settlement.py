"""Settlement timing, account separation and cash conservation."""

from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from app.portfolio_domain.cash import CashMovement, PortfolioCashService
from app.portfolio_domain.ledger import LedgerState
from app.portfolio_domain.money import ONE, ZERO
from app.portfolio_domain.nav import daily_performance, nav_total
from app.portfolio_domain.types import Entry
from hypothesis import given
from hypothesis import strategies as st

TRADE_DATE = date(2026, 2, 2)
SETTLE_DATE = date(2026, 2, 4)


def movement(
    amount: str, *, settlement: date = SETTLE_DATE, currency: str = "USD", account: str = "A"
) -> CashMovement:
    return CashMovement("trade-1", currency, D(amount), ONE, TRADE_DATE, settlement, account)


def test_buy_creates_pending_payable_without_spending_settled_cash_early() -> None:
    service = PortfolioCashService()
    service.record(movement("1000", settlement=TRADE_DATE))
    service.record(movement("-400"))
    balance = service.balance("USD", TRADE_DATE)
    assert balance.economic == D("600")
    assert balance.settled == D("1000")
    assert balance.receivable == ZERO
    assert balance.payable == D("400")
    assert balance.available == D("600")


def test_unsettled_sale_is_not_available_for_withdrawal() -> None:
    service = PortfolioCashService()
    service.record(movement("100", settlement=TRADE_DATE))
    service.record(movement("600"))
    before = service.balance("USD", TRADE_DATE)
    assert before.economic == D("700")
    assert before.receivable == D("600")
    assert before.available == D("100")
    after = service.balance("USD", SETTLE_DATE)
    assert after.settled == after.economic == after.available == D("700")
    assert after.payable == after.receivable == ZERO


def test_receivables_and_payables_remain_gross_when_net_cash_is_zero() -> None:
    service = PortfolioCashService()
    service.record(movement("500"))
    service.record(movement("-500"))
    balance = service.balance("USD", TRADE_DATE)
    assert balance.economic == ZERO
    assert balance.receivable == balance.payable == D("500")
    assert balance.available == D("-500")
    assert "USD" in service.balances(TRADE_DATE)


def test_query_before_trade_date_has_no_cash_or_pending_legs() -> None:
    service = PortfolioCashService([movement("100")])
    previous = TRADE_DATE - timedelta(days=1)
    assert service.balance("USD", previous).economic == ZERO
    assert service.balances(previous) == {}
    assert service.pending(previous) == []


def test_pending_interval_is_inclusive_trade_exclusive_settlement() -> None:
    service = PortfolioCashService([movement("100")])
    assert len(service.pending(TRADE_DATE)) == 1
    assert len(service.pending(SETTLE_DATE - timedelta(days=1))) == 1
    assert service.pending(SETTLE_DATE) == []
    assert service.settlement_dates() == {SETTLE_DATE}


def test_native_currencies_never_net_against_each_other() -> None:
    service = PortfolioCashService()
    service.record(movement("1000", currency="SGD", settlement=TRADE_DATE))
    service.record(movement("-700", currency="USD"))
    assert service.balance("SGD", TRADE_DATE).economic == D("1000")
    assert service.balance("USD", TRADE_DATE).economic == D("-700")
    assert list(service.balances(TRADE_DATE)) == ["SGD", "USD"]


def test_account_query_does_not_use_another_accounts_funding() -> None:
    service = PortfolioCashService()
    service.record(movement("1000", account="A", settlement=TRADE_DATE))
    service.record(movement("-400", account="B"))
    assert service.balance("USD", TRADE_DATE, "A").available == D("1000")
    assert service.balance("USD", TRADE_DATE, "B").available == D("-400")
    assert service.balance("USD", TRADE_DATE).available == D("600")
    assert service.balance("USD", TRADE_DATE, "unknown").economic == ZERO


def test_cash_book_uses_each_legs_recorded_fx() -> None:
    service = PortfolioCashService()
    service.record(replace(movement("1000"), fx=D("1.3")))
    service.record(replace(movement("-200"), fx=D("1.4")))
    assert service.balance("USD", TRADE_DATE).book_base == D("1020")
    assert service.balance("USD", TRADE_DATE).economic == D("800")


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_cash_is_rejected_without_recording(value: str) -> None:
    service = PortfolioCashService()
    with pytest.raises(ValueError, match="finite"):
        service.record(movement(value))
    assert not service.movements


@pytest.mark.parametrize("value", ["0", "-1", "NaN", "Infinity"])
def test_invalid_cash_fx_is_rejected(value: str) -> None:
    service = PortfolioCashService()
    with pytest.raises(ValueError):
        service.record(replace(movement("100"), fx=D(value)))
    assert not service.movements


def test_settlement_before_trade_is_rejected() -> None:
    service = PortfolioCashService()
    with pytest.raises(ValueError, match="precede"):
        service.record(movement("100", settlement=TRADE_DATE - timedelta(days=1)))


def test_ledger_carries_account_and_settlement_on_both_trade_and_fee() -> None:
    state = LedgerState()
    entry = Entry(
        "buy",
        TRADE_DATE,
        "BUY",
        "USD",
        D("2"),
        D("100"),
        commission=D("3"),
        instrument_id="AAPL",
        settle_date=SETTLE_DATE,
        account_id="account-x",
    )
    state.apply(entry)
    pending = state.cash_service.pending(TRADE_DATE)
    assert [item.description for item in pending] == ["TRADE", "CHARGES"]
    assert {item.account_id for item in pending} == {"account-x"}
    assert {item.transaction_id for item in pending} == {"buy"}
    assert sum(item.amount for item in pending) == D("-203")
    state.advance(SETTLE_DATE)
    assert state.cash_service.balance("USD", SETTLE_DATE).settled == D("-203")
    assert state.lots["AAPL"].quantity == D("2")


def test_fx_conversion_preserves_base_cash_book_and_creates_two_legs() -> None:
    state = LedgerState()
    state.apply(Entry("deposit", TRADE_DATE, "DEPOSIT", "SGD", amount=D("1300")))
    state.apply(
        Entry(
            "fx",
            TRADE_DATE,
            "FX_CONVERSION",
            "SGD",
            amount=D("1300"),
            metadata={"to_currency": "USD", "to_amount": "1000"},
            settle_date=SETTLE_DATE,
        )
    )
    assert state.cash["SGD"] == ZERO
    assert state.cash["USD"] == D("1000")
    assert state.cash_book_base == D("1300")
    assert state.external_flows == D("1300")
    pending = state.cash_service.pending(TRADE_DATE)
    assert {item.description for item in pending} == {"FX_SOLD", "FX_BOUGHT"}
    assert sum(item.amount * item.fx for item in pending) == ZERO


@pytest.mark.parametrize(
    "destination,received",
    [("USD", "0"), ("SGD", "100"), ("US", "100"), ("123", "100"), ("USD", "NaN")],
)
def test_invalid_fx_conversion_does_not_post_first_leg(destination: str, received: str) -> None:
    state = LedgerState()
    with pytest.raises(ValueError):
        state.apply(
            Entry(
                "fx",
                TRADE_DATE,
                "FX_CONVERSION",
                "SGD",
                amount=D("130"),
                metadata={"to_currency": destination, "to_amount": received},
            )
        )
    assert state.cash == {}
    assert state.cash_book_base == ZERO
    assert not state.cash_service.movements


def test_settlement_changes_balance_sheet_presentation_not_nav() -> None:
    state = LedgerState()
    state.apply(Entry("deposit", TRADE_DATE, "DEPOSIT", "USD", amount=D("1000")))
    state.apply(
        Entry(
            "buy",
            TRADE_DATE,
            "BUY",
            "USD",
            D("4"),
            D("100"),
            instrument_id="AAPL",
            settle_date=SETTLE_DATE,
        )
    )
    before = state.cash_service.balance("USD", TRADE_DATE)
    after = state.cash_service.balance("USD", SETTLE_DATE)
    first = nav_total(
        before.settled, [D("420")], {"receivables": before.receivable, "payables": before.payable}
    )
    second = nav_total(
        after.settled, [D("420")], {"receivables": after.receivable, "payables": after.payable}
    )
    assert first["nav"] == second["nav"] == D("1020")
    assert first["payables"] == D("400")
    assert second["payables"] == ZERO
    assert daily_performance(first["nav"], second["nav"], ZERO) == (ZERO, ZERO)


def test_historical_ledger_replay_rejects_backwards_time() -> None:
    state = LedgerState()
    state.advance(SETTLE_DATE)
    with pytest.raises(ValueError, match="chronological"):
        state.apply(Entry("past", TRADE_DATE, "DEPOSIT", "USD", amount=ONE))
    with pytest.raises(ValueError, match="backwards"):
        state.advance(TRADE_DATE)
    assert state.last_date == SETTLE_DATE
    assert state.cash == {}


@given(amounts=st.lists(st.integers(-100000, 100000), min_size=1, max_size=40))
def test_settlement_cash_identity_holds_for_mixed_inflows_outflows(amounts: list[int]) -> None:
    service = PortfolioCashService()
    for index, amount in enumerate(amounts):
        settlement = TRADE_DATE if index % 2 else SETTLE_DATE
        service.record(movement(str(amount), settlement=settlement))
    before = service.balance("USD", TRADE_DATE)
    assert before.economic == before.settled + before.receivable - before.payable
    assert before.available == before.settled - before.payable
    assert before.available <= before.economic
    after = service.balance("USD", SETTLE_DATE)
    assert after.economic == after.settled == after.available == D(sum(amounts))
    assert after.receivable == after.payable == ZERO
