"""Reconciliation preserves incomplete books and validates persisted financial inputs."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app import models
from app.database import get_session
from app.portfolio_api import router
from app.portfolio_operations import PortfolioLedgerService, PortfolioReconciliationService
from app.portfolio_valuation import PortfolioValuationService
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import JsonValue, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

OBJECT = TypeAdapter(dict[str, JsonValue])
ROWS = TypeAdapter(list[dict[str, JsonValue]])


@pytest.fixture
def reconciliation_client(ledger_session: Session) -> Iterator[TestClient]:
    application = FastAPI()
    application.include_router(router)

    def session_override() -> Iterator[Session]:
        yield ledger_session

    application.dependency_overrides[get_session] = session_override
    with TestClient(application, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def reference(monkeypatch: pytest.MonkeyPatch) -> dict[str, JsonValue]:
    data: dict[str, JsonValue] = {
        "portfolio": {"id": "book", "nav": "100.00000000"},
        "as_of": "2026-01-09T20:00:00+00:00",
        "cash": [],
        "positions": [],
        "transactions": [],
    }

    def latest(
        self: PortfolioValuationService, portfolio_key: str | None = None
    ) -> dict[str, JsonValue]:
        return data

    monkeypatch.setattr(PortfolioValuationService, "latest", latest)
    return data


def snapshot(session: Session, payload: dict[str, JsonValue]) -> models.BrokerAccountSnapshot:
    row = models.BrokerAccountSnapshot(
        portfolio_id="book",
        external_reference="fictional-reconciliation",
        as_of=datetime(2026, 1, 9, 20, tzinfo=UTC),
        source="TEST PAPER",
        connected=True,
        nav=Decimal("100.00000000"),
        currency="SGD",
        payload=payload,
    )
    session.add(row)
    session.commit()
    return row


def test_missing_internal_nav_creates_a_json_safe_warning_and_keeps_its_identity(
    ledger_session: Session, reference: dict[str, JsonValue]
) -> None:
    reference["portfolio"] = {"id": "book", "nav": None}
    broker = snapshot(ledger_session, {})
    service = PortfolioReconciliationService(ledger_session)
    first = OBJECT.validate_python(service.reconcile("TEST_BOOK"), strict=True)
    items = ROWS.validate_python(first["items"], strict=True)
    assert first["state"] == "BREAKS" and len(items) == 1
    assert items[0] == {
        "type": "NAV_MISMATCH",
        "key": "NAV",
        "internal": None,
        "external": "100.00000000",
        "difference": None,
        "severity": "WARN",
        "id": items[0]["id"],
    }
    json.dumps(first, allow_nan=False)
    second = OBJECT.validate_python(service.reconcile("TEST_BOOK"), strict=True)
    assert second["items"] == first["items"]
    breaks = ledger_session.scalars(select(models.PortfolioReconciliationBreak)).all()
    assert len(breaks) == 1 and breaks[0].external_snapshot_id == broker.id
    assert breaks[0].payload["external"] == "100.00000000"
    reference["portfolio"] = {"id": "book", "nav": "100.00000000"}
    assert service.reconcile("TEST_BOOK")["state"] == "MATCHED"
    assert breaks[0].state == "RESOLVED"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cash", None),
        ("cash", {}),
        ("cash", [{"currency": 1, "amount": "2"}]),
        ("positions", [False]),
        ("positions", [{"symbol": ["AAA"], "quantity": "1"}]),
        ("fills", [{"execution_id": [], "quantity": "1", "price": "2"}]),
        ("fills", [{"execution_id": "F1", "quantity": "1"}]),
        ("account_fingerprint", []),
    ],
)
def test_malformed_snapshot_fails_before_persisting_breaks(
    ledger_session: Session, reference: dict[str, JsonValue], field: str, value: JsonValue
) -> None:
    snapshot(ledger_session, {field: value})
    with pytest.raises(ValueError):
        PortfolioReconciliationService(ledger_session).reconcile("TEST_BOOK")
    assert not ledger_session.scalars(select(models.PortfolioReconciliationBreak)).all()


@pytest.mark.parametrize("value", [True, "NaN", "Infinity", "1e17", {}, []])
def test_missing_counterpart_does_not_bypass_financial_validation(
    ledger_session: Session, reference: dict[str, JsonValue], value: JsonValue
) -> None:
    reference["cash"] = [{"currency": "SGD", "amount": None}]
    snapshot(ledger_session, {"cash": [{"currency": "SGD", "amount": value}]})
    with pytest.raises(ValueError):
        PortfolioReconciliationService(ledger_session).reconcile("TEST_BOOK")
    assert not ledger_session.scalars(select(models.PortfolioReconciliationBreak)).all()


def test_zero_signed_values_and_existing_tolerances_are_preserved(
    ledger_session: Session, reference: dict[str, JsonValue]
) -> None:
    reference["cash"] = [{"currency": "SGD", "amount": "-5.00"}]
    reference["positions"] = [
        {"symbol": "AAA", "quantity": "-1.25000000", "average_cost": "0.0000"}
    ]
    broker = snapshot(
        ledger_session,
        {
            "cash": [{"currency": "SGD", "amount": "-5.01"}],
            "positions": [{"symbol": "AAA", "quantity": "-1.25000001", "average_cost": "0.0000"}],
        },
    )
    service = PortfolioReconciliationService(ledger_session)
    assert service.reconcile("TEST_BOOK")["state"] == "MATCHED"
    broker.payload = {
        **broker.payload,
        "cash": [{"currency": "SGD", "amount": "-5.01000001"}],
    }
    ledger_session.commit()
    result = OBJECT.validate_python(service.reconcile("TEST_BOOK"), strict=True)
    items = ROWS.validate_python(result["items"], strict=True)
    assert len(items) == 1
    assert items[0]["internal"] == "-5.00"
    assert items[0]["external"] == "-5.01000001"
    assert items[0]["difference"] == "0.01000001"


def test_unmatched_fill_preserves_all_source_fields_and_missing_commission(
    ledger_session: Session, reference: dict[str, JsonValue]
) -> None:
    fill: dict[str, JsonValue] = {
        "execution_id": "F1",
        "symbol": "AAA",
        "quantity": "1.25000000",
        "price": "120.00000000",
        "commission": None,
        "provider_extension": {"row": 4, "unavailable": None},
    }
    snapshot(ledger_session, {"fills": [fill]})
    result = OBJECT.validate_python(
        PortfolioReconciliationService(ledger_session).reconcile("TEST_BOOK"), strict=True
    )
    items = ROWS.validate_python(result["items"], strict=True)
    assert len(items) == 1 and items[0]["type"] == "UNMATCHED_BROKER_FILL"
    assert items[0]["external"] == fill
    assert isinstance(items[0]["external"], dict)
    assert list(items[0]["external"]) == list(fill)


def test_real_unpriced_position_keeps_nav_missing_and_reconciliation_available(
    ledger_session: Session,
) -> None:
    ledger_session.add(
        models.Instrument(
            id="UNPRICED",
            symbol="UNPRICED",
            name="Fictional security without market observations",
            country="Singapore",
            currency="SGD",
            asset_class="Equity",
            security_type="Common Stock",
            sector="Test",
        )
    )
    ledger_session.flush()
    PortfolioLedgerService(ledger_session).add(
        {
            "symbol": "UNPRICED",
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "quantity": "1",
            "price": "5",
            "currency": "SGD",
            "fx_rate_to_base": "1",
        },
        "TEST_BOOK",
    )
    snapshot(ledger_session, {})
    result = OBJECT.validate_python(
        PortfolioReconciliationService(ledger_session).reconcile("TEST_BOOK"), strict=True
    )
    items = ROWS.validate_python(result["items"], strict=True)
    nav = next(row for row in items if row["type"] == "NAV_MISMATCH")
    assert nav["internal"] is None and nav["difference"] is None
    assert result["state"] == "BREAKS"
    run = ledger_session.scalar(select(models.PortfolioValuationRun))
    assert run is not None and run.nav is None and run.status == "INCOMPLETE"
    json.dumps(result, allow_nan=False)


def test_api_missing_nav_returns_a_warning_not_a_server_error(
    reconciliation_client: TestClient, ledger_session: Session, reference: dict[str, JsonValue]
) -> None:
    reference["portfolio"] = {"id": "book", "nav": None}
    snapshot(ledger_session, {})
    response = reconciliation_client.post("/api/v1/operations/reconciliation?portfolio=TEST_BOOK")
    assert response.status_code == 200
    result = OBJECT.validate_json(response.content, strict=True)
    assert result["state"] == "BREAKS"


def test_api_invalid_recorded_data_is_rejected_without_exposing_values(
    reconciliation_client: TestClient, ledger_session: Session, reference: dict[str, JsonValue]
) -> None:
    snapshot(
        ledger_session,
        {"cash": [{"currency": "SGD", "amount": "private-invalid-financial-value"}]},
    )
    response = reconciliation_client.post("/api/v1/operations/reconciliation?portfolio=TEST_BOOK")
    assert response.status_code == 422
    assert response.json() == {"detail": "Recorded reconciliation inputs are invalid"}
    assert "private-invalid-financial-value" not in response.text
    assert not ledger_session.scalars(select(models.PortfolioReconciliationBreak)).all()


@pytest.mark.parametrize("nav", [None, 0, "-0.0100", "100000000000000000.00"])
def test_unconnected_state_does_not_require_comparison_rows_or_apply_comparison_limits(
    ledger_session: Session, reference: dict[str, JsonValue], nav: str | int | None
) -> None:
    reference.clear()
    reference.update({"portfolio": {"id": "book", "nav": nav}, "as_of": "2026-01-09"})
    result = PortfolioReconciliationService(ledger_session).reconcile("TEST_BOOK")
    assert result["state"] == "BROKER_NOT_CONNECTED"
    assert result["internal_nav"] == nav and result["items"] == []
