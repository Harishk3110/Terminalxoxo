"""Trade provenance, actor authenticity, reference identity and economic cash effects."""

from datetime import UTC, date, datetime
from decimal import Decimal as D

import pytest
from app import models
from app.portfolio_operations import PortfolioLedgerService
from app.transaction_context import TransactionContext, context_payload, record_context
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

BASE = "/api/v1/portfolios/book"


def test_aware_trade_timestamp_normalizes_to_utc() -> None:
    context = TransactionContext(trade_timestamp="2026-01-06T09:30:00+08:00")
    assert context.trade_timestamp == datetime(2026, 1, 6, 1, 30, tzinfo=UTC)
    assert context.trade_timestamp.tzinfo == UTC


@pytest.mark.parametrize("timestamp", ["2026-01-06T09:30:00", "bad-date", "2099-01-06T01:30:00Z"])
def test_invalid_timestamp_is_not_guessed(timestamp: str) -> None:
    with pytest.raises(ValueError):
        TransactionContext(trade_timestamp=timestamp)


def test_exchange_trade_date_may_differ_from_utc_by_one_day() -> None:
    metadata = {}
    context = record_context(
        {"trade_timestamp": "2026-01-05T23:30:00-05:00"}, metadata, date(2026, 1, 5)
    )
    assert context.trade_timestamp.date() == date(2026, 1, 6)
    assert metadata["trade_timestamp"].startswith("2026-01-06T04:30")
    with pytest.raises(ValueError, match="inconsistent"):
        record_context({"trade_timestamp": "2026-01-02T09:30:00Z"}, {}, date(2026, 1, 5))


@pytest.mark.parametrize("reference", ["line\nbreak", "nul\x00value", "x" * 161])
def test_reference_validation_rejects_control_characters_and_excess_length(reference: str) -> None:
    with pytest.raises(ValueError):
        TransactionContext(external_reference=reference)


def test_reference_normalization_preserves_printable_identity() -> None:
    context = TransactionContext(
        external_reference="  statement:row-001  ", broker_execution_id="   "
    )
    assert context.external_reference == "statement:row-001"
    assert context.broker_execution_id is None


def test_legacy_timestamp_failure_retains_original_metadata_without_inventing_time() -> None:
    metadata = {"trade_timestamp": "morning", "execution_id": "legacy-fill"}
    data = context_payload(metadata, None)
    assert data["trade_timestamp"] is None
    assert data["trade_timestamp_state"] == "NOT_RECORDED"
    assert "unvalidated" in data["context_warnings"][0]
    assert data["broker_execution_id"] == "legacy-fill"
    assert metadata["trade_timestamp"] == "morning"


@pytest.mark.parametrize(
    "name", ["external_reference", "broker_execution_id", "strategy_id", "thesis_id"]
)
def test_malformed_legacy_references_do_not_escape_as_objects(name: str) -> None:
    raw = {name: {"unvalidated": ["value"]}, "trade_timestamp": "2026-01-06T01:30:00Z"}
    view = context_payload(raw, "actual-creator")
    assert view[name] is None
    assert view["trade_timestamp_state"] == "RECORDED"
    assert view["created_by"] == "actual-creator"
    assert view["context_warnings"] == [f"Legacy {name} is unvalidated; original metadata retained"]
    assert raw[name] == {"unvalidated": ["value"]}


@pytest.mark.parametrize("reference", ["ref\x7f7", "ref\x857", "ref\u202e7"])
def test_reference_identifiers_reject_hidden_control_and_format_characters(reference: str) -> None:
    with pytest.raises(ValueError, match="control characters"):
        TransactionContext(external_reference=reference)


def test_transaction_exposes_original_reference_not_its_hash_and_survives_reload(
    client: TestClient, ledger_session: Session
) -> None:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "trade_timestamp": "2026-01-06T09:30:00+08:00",
            "settle_date": "2026-01-08",
            "symbol": "AAA",
            "quantity": "2",
            "price": "100",
            "commission": "1",
            "fee": ".5",
            "tax": ".2",
            "external_reference": " statement-001 ",
            "broker_execution_id": "paper-fill-7",
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["external_reference"] == "statement-001"
    assert len(created["external_key"]) == 64
    assert created["external_key"] != created["external_reference"]
    assert created["broker_execution_id"] == "paper-fill-7"
    assert created["reconciliation_state"] == "INTERNAL_ONLY"
    assert D(created["net_amount"]) == D("-201.7")
    ledger_session.expunge_all()
    actual = client.get(BASE + "/transactions/" + created["id"]).json()
    assert datetime.fromisoformat(actual["trade_timestamp"]) == datetime(
        2026, 1, 6, 1, 30, tzinfo=UTC
    )
    assert D(actual["net_amount"]) == D("-201.7")
    assert actual["external_reference"] == "statement-001"
    duplicate = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": "2",
            "price": "100",
            "external_reference": "statement-001",
        },
    )
    assert duplicate.json() == {"duplicate": True, "id": created["id"]}


def test_actual_creator_is_read_from_creation_audit_not_client_metadata(
    client: TestClient, ledger_session: Session
) -> None:
    ledger_session.add(
        models.User(
            id="creator", email="test@example.invalid", password_hash="test-only", role="ADMIN"
        )
    )
    ledger_session.commit()
    created = PortfolioLedgerService(ledger_session).add(
        {
            "transaction_type": "FEE",
            "trade_date": "2026-01-06",
            "amount": "2",
            "metadata": {"created_by": "forged-user", "actor_user_id": "forged-user"},
        },
        "book",
        actor="creator",
    )
    ledger_session.commit()
    row = client.get(BASE + "/transactions/" + created["id"]).json()
    assert row["created_by"] == "creator"
    assert row["creator_state"] == "AUDIT_LOG"
    assert "created_by" not in row["metadata"]
    assert "actor_user_id" not in row["metadata"]
    assert row["trade_timestamp"] is None
    assert row["trade_timestamp_state"] == "NOT_RECORDED"


def test_creation_audit_contains_context_and_does_not_claim_broker_execution(
    client: TestClient, ledger_session: Session
) -> None:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "FEE",
            "trade_date": "2026-01-06",
            "amount": "2",
            "external_reference": "manual-expense",
            "metadata": {"execution_id": "paper-reference"},
        },
    )
    assert response.status_code == 201, response.text
    row = response.json()
    assert row["broker_execution_id"] == "paper-reference"
    audit = ledger_session.scalar(
        select(models.AuditLog).where(
            models.AuditLog.resource_id == row["id"],
            models.AuditLog.action == "LEDGER_TRANSACTION_CREATED",
        )
    )
    assert audit.metadata_json["context"]["broker_execution_id"] == "paper-reference"
    assert audit.metadata_json["source"] == "MANUAL"
    assert row["created_by"] is None


def test_strategy_and_thesis_links_are_validated_and_returned(
    client: TestClient, ledger_session: Session
) -> None:
    ledger_session.add(
        models.StrategyDefinition(
            id="strategy",
            name="Test allocation",
            strategy_type="MANUAL",
            description="Test link",
            status="RESEARCH",
        )
    )
    ledger_session.add(
        models.InvestmentThesis(
            id="thesis",
            instrument_id="AAA",
            title="Test thesis",
            thesis_state="DRAFT",
            summary="Test link",
        )
    )
    ledger_session.commit()
    data = {
        "transaction_type": "BUY",
        "trade_date": "2026-01-06",
        "symbol": "AAA",
        "quantity": "1",
        "price": "100",
        "strategy_id": "strategy",
        "thesis_id": "thesis",
    }
    response = client.post(BASE + "/transactions", json=data)
    assert response.status_code == 201, response.text
    assert response.json()["strategy_id"] == "strategy"
    assert response.json()["thesis_id"] == "thesis"
    invalid = client.post(BASE + "/transactions", json={**data, "thesis_id": "unknown"})
    assert invalid.status_code == 422
    assert ledger_session.scalar(select(func.count(models.PortfolioTransaction.id))) == 2


def test_entry_options_returns_actual_policy_accounts_and_reference_records(
    client: TestClient, ledger_session: Session
) -> None:
    from app.portfolio_domain.types import TRANSACTION_TYPES
    from app.portfolio_operations import CURRENCIES

    ledger_session.add(
        models.StrategyDefinition(
            id="strategy",
            name="Test allocation",
            strategy_type="MANUAL",
            description="Test link",
            status="RESEARCH",
        )
    )
    ledger_session.add(
        models.InvestmentThesis(
            id="thesis",
            instrument_id="AAA",
            title="Test thesis",
            thesis_state="DRAFT",
            summary="Test link",
        )
    )
    ledger_session.commit()
    response = client.get(BASE + "/entry-options")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["portfolio"]["id"] == "book"
    assert data["portfolio"]["configuration"]["allow_short"] is True
    assert data["portfolio"]["accounts"] == [
        {"id": "account", "name": "Test account", "type": "INTERNAL", "provider": None}
    ]
    assert set(data["transaction_types"]) == TRANSACTION_TYPES
    assert set(data["currencies"]) == CURRENCIES
    assert data["strategies"] == [
        {"id": "strategy", "name": "Test allocation", "state": "RESEARCH"}
    ]
    assert data["theses"] == [
        {"id": "thesis", "title": "Test thesis", "state": "DRAFT", "instrument_id": "AAA"}
    ]
    assert client.get("/api/v1/portfolios/TEST_BOOK/entry-options").json() == data
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == 0


def test_entry_options_empty_research_lists_and_missing_portfolio_are_explicit(
    client: TestClient,
) -> None:
    data = client.get(BASE + "/entry-options").json()
    assert data["strategies"] == []
    assert data["theses"] == []
    response = client.get("/api/v1/portfolios/missing/entry-options")
    assert response.status_code == 404
    assert response.json()["detail"] == "Portfolio not found"


def test_void_and_correction_change_current_cash_effects_but_not_original_rows(
    client: TestClient,
) -> None:
    created = client.post(
        BASE + "/transactions",
        json={"transaction_type": "FEE", "trade_date": "2026-01-06", "amount": "2"},
    ).json()
    identifier = created["id"]
    client.put(
        BASE + "/transactions/" + identifier,
        json={
            "expected_version": 1,
            "reason": "Correct statement expense",
            "changes": {"amount": "3"},
        },
    ).raise_for_status()
    corrected = client.get(BASE + "/transactions/" + identifier).json()
    assert D(corrected["net_amount"]) == D("-3")
    client.request(
        "DELETE",
        BASE + "/transactions/" + identifier,
        json={"expected_version": 2, "reason": "Void duplicate fee"},
    ).raise_for_status()
    voided = client.get(BASE + "/transactions/" + identifier).json()
    assert voided["net_amount"] is None
    assert voided["cash_effect_state"] == "NOT_REPLAYED"
    assert D(voided["revisions"][0]["before"]["entry"]["amount"]) == D("2")


def test_backdated_summary_does_not_invent_cash_effects_for_later_entries(
    client: TestClient,
) -> None:
    future = client.post(
        BASE + "/transactions",
        json={"transaction_type": "DEPOSIT", "trade_date": "2026-01-08", "amount": "50"},
    ).json()
    summary = client.get(BASE + "/summary?end=2026-01-06").json()
    row = next(item for item in summary["transactions"] if item["id"] == future["id"])
    assert row["net_amount"] is None
    assert row["net_cash_by_currency"] == []
    assert row["cash_effect_state"] == "NOT_REPLAYED"


@pytest.mark.parametrize(
    "extra",
    [
        {"trade_timestamp": "2026-01-06T12:00:00"},
        {"trade_timestamp": "2025-01-06T12:00:00Z"},
        {"external_reference": "bad\x00reference"},
        {"broker_execution_id": "x" * 161},
        {"created_by": "forged"},
    ],
)
def test_invalid_context_leaves_no_transaction_or_audit(
    client: TestClient, ledger_session: Session, extra: dict
) -> None:
    response = client.post(
        BASE + "/transactions",
        json={"transaction_type": "FEE", "trade_date": "2026-01-06", "amount": "2", **extra},
    )
    assert response.status_code == 422, response.text
    assert ledger_session.scalar(select(func.count(models.PortfolioTransaction.id))) == 1
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == 0
