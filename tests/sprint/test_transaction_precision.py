"""Reject silent input quantization at the legacy eight-decimal storage boundary."""

from datetime import date
from decimal import Decimal as D
from typing import Any

import pytest
from app import models
from app.portfolio_domain.money import stored_decimal
from app.portfolio_valuation import PortfolioValuationService
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

BASE = "/api/v1/portfolios/book"


@pytest.mark.parametrize(
    "value", ["0.000000001", "1.123456789", "-1.123456789", "10000000000000000", "NaN", "Infinity"]
)
def test_storage_decimal_rejects_unrepresentable_values(value: str) -> None:
    with pytest.raises(ValueError):
        stored_decimal(value, "quantity")


@pytest.mark.parametrize(
    "value", ["0.00000001", "1.230000000", "9999999999999999", "-10.12345678", "0"]
)
def test_storage_decimal_retains_exact_representable_value(value: str) -> None:
    assert stored_decimal(value) == D(value)


@pytest.mark.parametrize(
    "field", ["quantity", "price", "fee", "commission", "tax", "contract_multiplier"]
)
def test_trade_precision_failure_leaves_no_partial_transaction_or_event(
    client: TestClient,
    ledger_session: Session,
    field: str,
) -> None:
    before = ledger_session.scalar(select(func.count(models.PortfolioTransaction.id)))
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": "1",
            "price": "100",
            field: "1.123456789",
        },
    )
    assert response.status_code == 422, response.text
    assert "eight decimal places" in response.json()["detail"]
    assert ledger_session.scalar(select(func.count(models.PortfolioTransaction.id))) == before
    assert ledger_session.scalar(select(func.count(models.TradeEvent.id))) == 0
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == 0


def test_sub_storage_unit_fee_is_not_saved_as_a_zero_expense(client: TestClient) -> None:
    response = client.post(
        BASE + "/transactions",
        json={"transaction_type": "FEE", "trade_date": "2026-01-06", "amount": "0.000000001"},
    )
    assert response.status_code == 422
    assert len(client.get(BASE + "/transactions").json()["items"]) == 1


def test_derived_gross_must_also_fit_storage_instead_of_silently_rounding(
    client: TestClient,
) -> None:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": "0.12345678",
            "price": "123.12345678",
        },
    )
    assert response.status_code == 422
    assert "gross amount supports at most eight" in response.json()["detail"]


def test_supported_fractional_trade_replays_identically_after_expunging_session(
    client: TestClient,
    ledger_session: Session,
) -> None:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": "0.123456",
            "price": "101.23",
            "commission": "0.01000001",
        },
    )
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    before = PortfolioValuationService(ledger_session).calculate("book", date(2026, 1, 6))
    ledger_session.expunge_all()
    after = PortfolioValuationService(ledger_session).calculate("book", date(2026, 1, 6))
    assert before["portfolio"]["nav"] == after["portfolio"]["nav"]
    assert before["reconciliation"].keys() == after["reconciliation"].keys()
    for key, value in before["reconciliation"].items():
        actual = after["reconciliation"][key]
        assert actual == value if key == "state" or value is None else D(actual) == D(value)
    persisted = next(row for row in after["transactions"] if row["id"] == identifier)
    assert D(persisted["quantity"]) == D("0.123456")
    assert D(persisted["gross_amount"]) == D("0.123456") * D("101.23")
    assert D(persisted["commission"]) == D(".01000001")


def test_explicit_fx_is_not_silently_rounded(client: TestClient) -> None:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "DEPOSIT",
            "trade_date": "2026-01-06",
            "currency": "USD",
            "amount": "100",
            "fx_rate_to_base": "1.123456789",
        },
    )
    assert response.status_code == 422
    assert "transaction FX" in response.json()["detail"]


def test_resolved_fx_records_observed_and_booked_rates(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.price_sources import FxRateResolver

    original = FxRateResolver.resolve

    def resolve(self: FxRateResolver, currency: str, base: str, at: Any) -> Any:
        if currency == "USD" and base == "SGD":
            _, provenance = original(self, currency, base, at)
            return D("1.333333335"), {**provenance, "source": "Precision fixture"}
        return original(self, currency, base, at)

    monkeypatch.setattr(FxRateResolver, "resolve", resolve)
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "DEPOSIT",
            "trade_date": "2026-01-06",
            "currency": "USD",
            "amount": "100",
        },
    )
    assert response.status_code == 201, response.text
    row = response.json()
    assert D(row["fx_rate_to_base"]) == D("1.33333334")
    assert row["metadata"]["fx_recording"] == {
        "observed_rate": "1.333333335",
        "recorded_rate": "1.33333334",
        "rounding": "ROUND_HALF_EVEN",
        "decimal_places": 8,
    }


def test_correction_rejects_precision_loss_without_appending_revision(
    client: TestClient, ledger_session: Session
) -> None:
    response = client.put(
        BASE + "/transactions/deposit",
        json={
            "expected_version": 1,
            "reason": "Correct contributed cash",
            "changes": {"amount": "10000.000000001"},
        },
    )
    assert response.status_code == 422
    assert ledger_session.scalar(select(func.count(models.TransactionRevision.id))) == 0


def test_manual_metadata_cannot_forge_provider_fx_rounding(client: TestClient) -> None:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "DEPOSIT",
            "trade_date": "2026-01-06",
            "currency": "USD",
            "amount": "100",
            "fx_rate_to_base": "1.3",
            "metadata": {"fx_recording": {"observed_rate": "999"}},
        },
    )
    assert response.status_code == 201, response.text
    assert "fx_recording" not in response.json()["metadata"]
    assert response.json()["metadata"]["fx_source"] == "USER PROVIDED TRANSACTION FX"


def test_local_sqlite_rejects_large_fractional_amount_that_its_driver_changes(
    client: TestClient,
) -> None:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "DEPOSIT",
            "trade_date": "2026-01-06",
            "amount": "123456789012.12345678",
        },
    )
    assert response.status_code == 422, response.text
    assert "round-trip through local SQLite storage" in response.json()["detail"]
    assert len(client.get(BASE + "/transactions").json()["items"]) == 1


def test_balance_adjustment_obeys_the_same_sqlite_roundtrip_guard(client: TestClient) -> None:
    response = client.post(
        BASE + "/balances",
        json={
            "effective_date": "2026-01-06",
            "bucket": "receivables",
            "currency": "SGD",
            "amount": "123456789012.12345678",
            "reason": "Unsafe local storage value",
        },
    )
    assert response.status_code == 422, response.text
    assert "round-trip through local SQLite storage" in response.json()["detail"]
    assert client.get(BASE + "/balances").json()["items"] == []
