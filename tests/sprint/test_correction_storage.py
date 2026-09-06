"""Corrections cannot bypass source-entry storage bounds or inherit false FX provenance."""

from decimal import Decimal as D

import pytest
from app import models
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

BASE = "/api/v1/portfolios/book"


def foreign_deposit(client: TestClient) -> dict:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "DEPOSIT",
            "trade_date": "2026-01-06",
            "currency": "USD",
            "amount": "100",
            "external_reference": "Funding-statement-01",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def revise(client: TestClient, identifier: str, changes: dict[str, str]):
    return client.put(
        BASE + "/transactions/" + identifier,
        json={
            "expected_version": 1,
            "reason": "Correct recorded foreign funding",
            "changes": changes,
        },
    )


@pytest.mark.parametrize(
    "field", ["amount", "quantity", "price", "commission", "fee", "tax", "fx_rate_to_base"]
)
def test_correction_rejects_sqlite_loss_on_every_financial_input(
    client: TestClient, ledger_session: Session, field: str
) -> None:
    original = foreign_deposit(client)
    count = ledger_session.scalar(select(func.count(models.AuditLog.id)))
    response = revise(client, original["id"], {field: "123456789012.12345678"})
    assert response.status_code == 422, response.text
    assert "round-trip through local SQLite storage" in response.json()["detail"]
    assert ledger_session.scalar(select(func.count(models.TransactionRevision.id))) == 0
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == count
    current = client.get(BASE + "/transactions/" + original["id"]).json()
    assert current["audit_version"] == 1
    assert D(current["gross_amount"]) == D(100)
    assert current["metadata"] == original["metadata"]


def test_corrected_base_value_must_fit_the_same_bounds_as_new_recorded_fx(
    client: TestClient,
) -> None:
    original = foreign_deposit(client)
    response = revise(client, original["id"], {"fx_rate_to_base": "100000000000000"})
    assert response.status_code == 422, response.text
    assert "stored base value" in response.json()["detail"]
    assert client.get(BASE + "/transactions/" + original["id"]).json()["audit_version"] == 1


def test_corrected_fx_is_explicit_while_original_provider_evidence_remains_in_audit(
    client: TestClient, ledger_session: Session
) -> None:
    original = foreign_deposit(client)
    assert original["metadata"]["fx_source"] == "TEST"
    response = revise(client, original["id"], {"fx_rate_to_base": "1.23456789"})
    assert response.status_code == 200, response.text
    ledger_session.expire_all()
    current = client.get(BASE + "/transactions/" + original["id"]).json()
    assert current["metadata"]["fx_source"] == "AUDITED MANUAL CORRECTION"
    assert "fx_recording" not in current["metadata"]
    assert current["metadata"]["fx_correction"] == {
        "previous_rate": original["fx_rate_to_base"],
        "recorded_rate": "1.23456789",
        "reason": "Correct recorded foreign funding",
    }
    assert current["external_reference"] == "Funding-statement-01"
    assert D(current["net_base_value"]) == D("123.456789")
    revision = current["revisions"][0]
    assert revision["before"]["entry"]["metadata"] == original["metadata"]
    assert revision["after"]["entry"]["metadata"] == current["metadata"]
    raw = ledger_session.get(models.PortfolioTransaction, original["id"])
    assert raw is not None and raw.fx_rate_to_base == D("1.3")
    detail = ledger_session.scalar(
        select(models.TransactionDetail).where(
            models.TransactionDetail.transaction_id == original["id"]
        )
    )
    assert detail is not None and detail.metadata_json == original["metadata"]


def test_note_only_amendment_does_not_relabel_a_provider_fx_observation(client: TestClient) -> None:
    original = foreign_deposit(client)
    response = revise(client, original["id"], {"notes": "Clarify statement reference"})
    assert response.status_code == 200, response.text
    current = client.get(BASE + "/transactions/" + original["id"]).json()
    assert current["metadata"] == original["metadata"]
    assert current["notes"] == "Clarify statement reference"
    assert "fx_correction" not in current["metadata"]


def test_void_retains_last_corrected_values_for_audit_but_removes_cash_effect(
    client: TestClient,
) -> None:
    original = foreign_deposit(client)
    response = revise(
        client,
        original["id"],
        {
            "amount": "120",
            "fx_rate_to_base": "1.4",
            "notes": "Corrected funding evidence",
        },
    )
    assert response.status_code == 200, response.text
    path = BASE + "/transactions/" + original["id"]
    corrected = client.get(path).json()
    voided = client.request(
        "DELETE",
        path,
        json={
            "expected_version": 2,
            "reason": "Funding was reversed in source statement",
        },
    )
    assert voided.status_code == 200, voided.text
    current = client.get(path).json()
    assert current["ledger_state"] == "VOID"
    assert current["audit_version"] == 3
    assert D(current["gross_amount"]) == D(120)
    assert D(current["fx_rate_to_base"]) == D("1.4")
    assert current["metadata"] == corrected["metadata"]
    assert current["notes"] == "Corrected funding evidence"
    assert current["net_amount"] is None
    assert current["cash_effect_state"] == "NOT_REPLAYED"
    summary = client.get(BASE + "/summary?end=2026-01-07").json()
    assert D(summary["portfolio"]["nav"]) == D(10000)
    assert summary["portfolio"]["total_pnl"] == "0.00"


def test_supported_fractional_correction_remains_exact_after_persisted_replay(
    client: TestClient, ledger_session: Session
) -> None:
    original = foreign_deposit(client)
    response = revise(
        client, original["id"], {"amount": "123.12345678", "commission": "0.00000001"}
    )
    assert response.status_code == 200, response.text
    ledger_session.expire_all()
    current = client.get(BASE + "/transactions/" + original["id"]).json()
    assert current["gross_amount"] == "123.12345678"
    assert D(current["commission"]) == D("0.00000001")
    assert D(current["net_amount"]) == D("123.12345677")
    assert D(current["net_base_value"]) == D("123.12345677") * D("1.3")
