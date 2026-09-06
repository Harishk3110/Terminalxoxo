"""Cash-effect reporting is derived from ledger movements, not transaction labels."""

from datetime import date
from decimal import Decimal as D

import pytest
from app.portfolio_domain.ledger import LedgerState
from app.portfolio_domain.transaction_cash import enrich_cash_effects
from app.portfolio_domain.types import AccountingPolicy, Entry
from hypothesis import given
from hypothesis import strategies as st

DAY = date(2026, 1, 5)


def cash_views(entries: list[Entry], policy: AccountingPolicy | None = None) -> list[dict]:
    state = LedgerState(policy or AccountingPolicy())
    for entry in entries:
        state.apply(entry)
    payloads = [{"id": entry.id, "currency": entry.currency} for entry in entries]
    enrich_cash_effects(payloads, entries, state.cash_service.movements)
    return payloads


@pytest.mark.parametrize(
    "kind,sign", [("DEPOSIT", 1), ("WITHDRAWAL", -1), ("TRANSFER_IN", 1), ("TRANSFER_OUT", -1)]
)
def test_cash_capital_movements_have_signed_net_amounts(kind: str, sign: int) -> None:
    row = cash_views([Entry("flow", DAY, kind, "USD", amount=D("100"), fx=D("1.3"), fee=D("1"))])[0]
    assert D(row["net_amount"]) == sign * D("100") - D("1")
    assert D(row["net_base_value"]) == (sign * D("100") - D("1")) * D("1.3")
    assert row["cash_effect_state"] == "REPLAYED"
    assert row["net_amount_basis"] == "SOURCE-CURRENCY ECONOMIC CASH IMPACT"


@pytest.mark.parametrize("kind", ["DIVIDEND", "INTEREST"])
def test_income_cash_effect_is_net_of_withholding_and_charges(kind: str) -> None:
    row = cash_views(
        [Entry("income", DAY, kind, "USD", amount=D("100"), tax=D("30"), fee=D("1"), fx=D("1.25"))]
    )[0]
    assert D(row["net_amount"]) == D("69")
    assert D(row["net_cash_base"]) == D("86.25")
    assert len(row["net_cash_by_currency"]) == 1


@pytest.mark.parametrize("kind", ["COMMISSION", "FEE", "TAX"])
def test_standalone_expenses_have_negative_cash_effects(kind: str) -> None:
    row = cash_views([Entry("cost", DAY, kind, "SGD", amount=D("3"))])[0]
    assert D(row["net_amount"]) == D("-3")
    assert D(row["net_base_value"]) == D("-3")


def test_buy_sell_short_cover_cash_effects_do_not_depend_on_cost_policy() -> None:
    entries = [
        Entry(
            "buy",
            DAY,
            "BUY",
            "SGD",
            quantity=D("3"),
            price=D("100"),
            instrument_id="AAA",
            commission=D("1"),
        ),
        Entry(
            "sell",
            DAY,
            "SELL",
            "SGD",
            quantity=D("1"),
            price=D("120"),
            instrument_id="AAA",
            fee=D("2"),
        ),
        Entry(
            "short",
            DAY,
            "SHORT",
            "SGD",
            quantity=D("2"),
            price=D("100"),
            instrument_id="BBB",
            commission=D("1"),
        ),
        Entry(
            "cover",
            DAY,
            "COVER",
            "SGD",
            quantity=D("1"),
            price=D("90"),
            instrument_id="BBB",
            fee=D("2"),
        ),
    ]
    before = cash_views(entries)
    capitalized = cash_views(
        entries, AccountingPolicy(capitalize_commissions=True, capitalize_fees=True)
    )
    assert {row["id"]: D(row["net_amount"]) for row in before} == {
        "buy": D("-301"),
        "sell": D("118"),
        "short": D("199"),
        "cover": D("-92"),
    }
    assert before == capitalized


def test_fx_conversion_keeps_both_legs_and_only_charges_reduce_total_base_cash() -> None:
    row = cash_views(
        [
            Entry(
                "fx",
                DAY,
                "FX_CONVERSION",
                "USD",
                amount=D("100"),
                fx=D("1.3"),
                fee=D("2"),
                commission=D("1"),
                metadata={"to_currency": "SGD", "to_amount": "130"},
            )
        ]
    )[0]
    assert D(row["net_amount"]) == D("-103")
    assert D(row["net_base_value"]) == D("-133.9")
    assert D(row["net_cash_base"]) == D("-3.9")
    legs = {leg["currency"]: D(leg["amount"]) for leg in row["net_cash_by_currency"]}
    assert legs == {"SGD": D("130"), "USD": D("-103")}


def test_non_cash_transfers_do_not_appear_as_cash_contributions() -> None:
    rows = cash_views(
        [
            Entry(
                "in",
                DAY,
                "TRANSFER_IN",
                "SGD",
                quantity=D("3"),
                price=D("100"),
                instrument_id="AAA",
            ),
            Entry(
                "out",
                DAY,
                "TRANSFER_OUT",
                "SGD",
                quantity=D("1"),
                price=D("110"),
                instrument_id="AAA",
            ),
        ]
    )
    assert all(D(row["net_amount"]) == 0 for row in rows)
    assert all(row["net_cash_by_currency"] == [] for row in rows)
    assert all(row["cash_effect_state"] == "REPLAYED" for row in rows)


def test_split_and_stock_only_spinoff_have_zero_cash_impact() -> None:
    rows = cash_views(
        [
            Entry("buy", DAY, "BUY", "SGD", quantity=D("3"), price=D("100"), instrument_id="AAA"),
            Entry("split", DAY, "SPLIT", "SGD", instrument_id="AAA", metadata={"ratio": "2"}),
            Entry(
                "reverse",
                DAY,
                "REVERSE_SPLIT",
                "SGD",
                instrument_id="AAA",
                metadata={"ratio": ".5"},
            ),
            Entry(
                "spinoff",
                DAY,
                "SPINOFF",
                "SGD",
                quantity=D("2"),
                instrument_id="AAA",
                metadata={"child_instrument_id": "BBB", "cost_allocation": ".25"},
            ),
        ]
    )
    assert [D(row["net_amount"]) for row in rows[1:]] == [D("0"), D("0"), D("0")]


def test_merger_cash_impact_uses_actual_parent_quantity_not_zero_entry_gross() -> None:
    entries = [
        Entry("buy", DAY, "BUY", "SGD", quantity=D("3"), price=D("100"), instrument_id="AAA"),
        Entry(
            "merger",
            DAY,
            "MERGER",
            "SGD",
            instrument_id="AAA",
            metadata={
                "child_instrument_id": "BBB",
                "exchange_ratio": "2",
                "cash_per_share": "10",
                "cash_cost_allocation": ".1",
            },
        ),
    ]
    merger = cash_views(entries)[-1]
    assert entries[-1].gross == 0
    assert D(merger["net_amount"]) == D("30")


@pytest.mark.parametrize("direction,expected", [("CREDIT", "20"), ("DEBIT", "-20")])
def test_explicit_correction_direction_controls_cash_impact(direction: str, expected: str) -> None:
    row = cash_views(
        [
            Entry(
                "adjust",
                DAY,
                "OTHER_ADJUSTMENT",
                "SGD",
                amount=D("20"),
                metadata={"direction": direction, "reason": "Correct internal balance"},
            )
        ]
    )[0]
    assert D(row["net_amount"]) == D(expected)


@given(
    amount=st.decimals(min_value="1", max_value="100000", places=4),
    fee=st.decimals(min_value="0", max_value="100", places=4),
    fx=st.decimals(min_value=".001", max_value="10", places=6),
)
def test_aggregate_reported_cash_effects_equal_replay_book_cash(amount: D, fee: D, fx: D) -> None:
    entries = [
        Entry("deposit", DAY, "DEPOSIT", "USD", amount=amount, fx=fx),
        Entry("fee", DAY, "FEE", "USD", amount=fee or D(".01"), fx=fx),
    ]
    ledger = LedgerState()
    for entry in entries:
        ledger.apply(entry)
    rows = [{"id": entry.id, "currency": entry.currency} for entry in entries]
    enrich_cash_effects(rows, entries, ledger.cash_service.movements)
    assert sum((D(row["net_cash_base"]) for row in rows), D("0")) == ledger.cash_book_base
