"""Boundary validation, precision and explicit policy contracts."""

from datetime import date
from decimal import Decimal as D

import pytest
from app.ledger_contracts import AmendmentRequest, EntryRecord, RevisionRequest, TransactionChanges
from app.portfolio_domain.money import ONE, ZERO, allocate, decimal, money
from app.portfolio_domain.nav import nav_total
from app.portfolio_domain.types import AccountingPolicy, CostMethod, Entry
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError


@pytest.mark.parametrize("value", [None, "", "abc", "1,000", True, object()])
def test_decimal_parser_rejects_non_numeric_inputs(value: object) -> None:
    with pytest.raises(ValueError, match="numeric"):
        decimal(value)


@pytest.mark.parametrize("value", ["NaN", "sNaN", "Infinity", "-Infinity", "10000000000000001"])
def test_decimal_parser_rejects_nonfinite_or_unbounded_inputs(value: str) -> None:
    with pytest.raises(ValueError, match="finite"):
        decimal(value)


def test_decimal_parser_keeps_fractional_precision_and_exact_bound() -> None:
    assert decimal("0.123456789123456789") == D("0.123456789123456789")
    assert decimal("1e16") == D("10000000000000000")
    assert decimal("-1e16") == D("-10000000000000000")
    assert decimal("-0", nonnegative=True) == ZERO


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1.005", "1.00"),
        ("1.015", "1.02"),
        ("-1.005", "-1.00"),
        ("-1.015", "-1.02"),
        ("-0.001", "0.00"),
    ],
)
def test_money_uses_half_even_display_rounding(value: str, expected: str) -> None:
    assert str(money(D(value))) == expected


def test_rounding_supports_currency_and_quantity_scales_without_mutating_input() -> None:
    value = D("123.456789123456")
    assert money(value, 0) == D("123")
    assert money(value, 3) == D("123.457")
    assert money(value, 8) == D("123.45678912")
    assert money(value, 12) == value
    assert str(value) == "123.456789123456"


@pytest.mark.parametrize("places", [-1, 13])
def test_invalid_rounding_precision_is_rejected(places: int) -> None:
    with pytest.raises(ValueError, match="places"):
        money(ONE, places)


@pytest.mark.parametrize("value", ["NaN", "Infinity"])
def test_nonfinite_rounding_is_rejected(value: str) -> None:
    with pytest.raises(ValueError, match="non-finite"):
        money(D(value))


def test_allocation_puts_residual_on_last_positive_weight_not_trailing_zero() -> None:
    result = allocate(ONE, [ONE, ONE, ONE, ZERO])
    assert len(result) == 4
    assert sum(result) == ONE
    assert result[-1] == ZERO
    assert result[2] == ONE - result[0] - result[1]


def test_signed_allocation_keeps_zero_weight_empty() -> None:
    assert allocate(D("-12"), [ZERO, ONE, D("2")]) == [ZERO, D("-4"), D("-8")]
    assert allocate(ZERO, [ONE, ONE]) == [ZERO, ZERO]


@pytest.mark.parametrize("weights", [[], [ZERO], [D("-1")], [D("NaN")], [D("Infinity")]])
def test_invalid_allocation_weights_raise_value_error(weights: list[D]) -> None:
    with pytest.raises(ValueError):
        allocate(ONE, weights)


def test_allocation_rejects_nonfinite_total() -> None:
    with pytest.raises(ValueError, match="total"):
        allocate(D("NaN"), [ONE])


@given(
    total=st.integers(-100000, 100000),
    weights=st.lists(st.integers(1, 1000), min_size=1, max_size=30),
)
def test_allocation_preserves_total_to_accounting_precision(total: int, weights: list[int]) -> None:
    allocated = allocate(D(total), [D(value) for value in weights])
    assert money(sum(allocated)) == money(D(total))
    assert len(allocated) == len(weights)
    assert (
        all(item >= ZERO for item in allocated)
        if total >= 0
        else all(item <= ZERO for item in allocated)
    )


def test_policy_default_retains_historical_cost_treatment() -> None:
    policy = AccountingPolicy.from_config({})
    assert policy.method == CostMethod.AVERAGE
    assert policy.capitalize_commissions is False
    assert policy.capitalize_fees is False


@pytest.mark.parametrize(
    "config",
    [
        {"accounting": []},
        {"accounting": {"method": "LIFO"}},
        {"accounting": {"capitalize_fees": "false"}},
        {"accounting": {"capitalize_commissions": 1}},
    ],
)
def test_invalid_stored_policy_is_not_silently_coerced(config: dict) -> None:
    with pytest.raises(ValueError):
        AccountingPolicy.from_config(config)


def test_policy_serialization_round_trip() -> None:
    policy = AccountingPolicy(CostMethod.FIFO, True, False)
    assert AccountingPolicy.from_config({"accounting": policy.to_dict()}) == policy


def test_entry_record_round_trip_preserves_decimal_dates_and_provenance() -> None:
    entry = Entry(
        "txn",
        date(2026, 1, 5),
        "BUY",
        "USD",
        D("1.125"),
        D("101.25"),
        fx=D("1.3456789"),
        instrument_id="AAA",
        metadata={"source_file_id": "file-1"},
        settle_date=date(2026, 1, 7),
        account_id="account-1",
    )
    payload = EntryRecord.from_entry(entry).model_dump(mode="json")
    assert payload["quantity"] == "1.125"
    assert payload["settle_date"] == "2026-01-07"
    restored = EntryRecord.model_validate(payload).to_entry()
    assert restored == entry


@pytest.mark.parametrize("currency", ["usd", "US", "USDD", "123", "U$D", "\u00c5BC"])
def test_entry_currency_is_ascii_iso_shape(currency: str) -> None:
    with pytest.raises(ValueError, match="Currency"):
        Entry("txn", date(2026, 1, 5), "DEPOSIT", currency, amount=ONE).validate()


def test_trade_with_conflicting_explicit_gross_is_rejected() -> None:
    entry = Entry(
        "txn",
        date(2026, 1, 5),
        "BUY",
        "USD",
        D("2"),
        D("100"),
        amount=D("150"),
        instrument_id="AAA",
    )
    with pytest.raises(ValueError, match="Gross amount"):
        entry.validate()


@pytest.mark.parametrize("reason", ["", "bad", "     ", "  x  "])
def test_correction_reason_cannot_be_empty_or_whitespace(reason: str) -> None:
    with pytest.raises(ValidationError):
        RevisionRequest(expected_version=1, reason=reason)


def test_revision_contract_rejects_unknown_fields_and_missing_expected_version() -> None:
    with pytest.raises(ValidationError):
        AmendmentRequest.model_validate({"reason": "Correct trade", "changes": {"quantity": "1"}})
    with pytest.raises(ValidationError):
        TransactionChanges.model_validate({"portfolio_id": "another"})


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "10000000000000001"])
def test_revision_amount_validation_is_bounded(value: str) -> None:
    with pytest.raises(ValidationError):
        TransactionChanges.model_validate({"amount": value})


def test_nav_rejects_unknown_balance_bucket_instead_of_ignoring_it() -> None:
    with pytest.raises(ValueError, match="Unknown NAV"):
        nav_total(ONE, [], {"unclassified": ONE})
