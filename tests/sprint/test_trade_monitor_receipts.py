"""Recorded trade metadata cannot replace ledger or risk evidence."""

import json
from collections.abc import Iterator

import pytest
from app import models
from app import portfolio_operations as operations
from app.database import get_session
from app.portfolio_api import router
from app.portfolio_operations import PortfolioLedgerService, TradeMonitorService
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import JsonValue, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

OBJECT = TypeAdapter(dict[str, JsonValue])


@pytest.fixture
def trade(ledger_session: Session) -> models.TradeEvent:
    created = PortfolioLedgerService(ledger_session).add(
        {
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": "1",
            "price": "120",
            "external_reference": "fictional-monitor-receipt",
        },
        "TEST_BOOK",
    )
    ledger_session.commit()
    row = ledger_session.get(models.TradeEvent, created["trade_event_id"])
    assert row is not None
    return row


@pytest.fixture
def risk(ledger_session: Session, trade: models.TradeEvent) -> models.TradeRiskSnapshot:
    row = ledger_session.scalar(
        select(models.TradeRiskSnapshot).where(models.TradeRiskSnapshot.trade_id == trade.id)
    )
    assert row is not None
    return row


@pytest.fixture
def trade_client(ledger_session: Session) -> Iterator[TestClient]:
    application = FastAPI()
    application.include_router(router)

    def session_override() -> Iterator[Session]:
        yield ledger_session

    application.dependency_overrides[get_session] = session_override
    with TestClient(application, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("id", "fabricated-id"),
        ("transaction_id", "fabricated-transaction"),
        ("review_state", "REVIEWED"),
        ("current_price", "999.00"),
        ("current_price_provenance", {"source": "LIVE"}),
        ("breaches", []),
        ("post_beta", 0),
        ("weight_after", 0),
        ("risk_as_of", "2099-01-01"),
        ("quantity", "100000"),
        ("currency", "USD"),
        ("ledger_state", "VOID"),
        ("created_by", "another-user"),
    ],
)
def test_event_extensions_cannot_replace_authoritative_evidence(
    ledger_session: Session, trade: models.TradeEvent, key: str, value: JsonValue
) -> None:
    trade.payload = {**trade.payload, key: value}
    ledger_session.commit()
    with pytest.raises(ValueError):
        TradeMonitorService(ledger_session).list("TEST_BOOK")
    assert trade.review_state == "REQUIRES_REVIEW"
    assert not ledger_session.scalars(select(models.TradeReview)).all()


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("beta", "NaN"),
        ("beta", True),
        ("positions", {}),
        ("positions", [{"symbol": "AAA", "weight": "Infinity"}]),
        ("positions", [{"symbol": ["AAA"], "weight": 0}]),
        ("exposures", {"sector": [{"name": "Test", "weight": []}]}),
        ("as_of", []),
    ],
)
def test_invalid_recorded_risk_is_rejected_even_with_missing_nav(
    ledger_session: Session, risk: models.TradeRiskSnapshot, key: str, value: JsonValue
) -> None:
    risk.after = {**risk.after, "nav": None, key: value}
    ledger_session.commit()
    with pytest.raises(ValueError):
        TradeMonitorService(ledger_session).list("TEST_BOOK")


def test_api_redacts_invalid_recorded_values(
    ledger_session: Session, risk: models.TradeRiskSnapshot, trade_client: TestClient
) -> None:
    risk.after = {**risk.after, "beta": "private-bad-recorded-value"}
    ledger_session.commit()
    response = trade_client.get("/api/v1/operations/trades?portfolio=TEST_BOOK")
    assert response.status_code == 422
    assert response.json() == {"detail": "Recorded trade-monitor inputs are invalid"}
    assert "private-bad-recorded-value" not in response.text


def test_event_symbol_cannot_disagree_with_effective_ledger(
    ledger_session: Session, trade: models.TradeEvent
) -> None:
    trade.payload = {**trade.payload, "symbol": "BBB"}
    ledger_session.commit()
    result = OBJECT.validate_python(TradeMonitorService(ledger_session).list("TEST_BOOK")[0])
    assert result["symbol"] == "AAA"
    assert result["weight_after"] != 0


@pytest.mark.parametrize(
    "field", ["external_reference", "source_file_id", "thesis_id", "strategy_id"]
)
def test_legacy_context_duplicates_cannot_replace_effective_ledger_context(
    ledger_session: Session, trade: models.TradeEvent, field: str
) -> None:
    service = TradeMonitorService(ledger_session)
    before = OBJECT.validate_python(service.list("TEST_BOOK")[0])
    trade.payload = {**trade.payload, field: "unrelated-recorded-context"}
    ledger_session.commit()
    after = OBJECT.validate_python(service.list("TEST_BOOK")[0])
    assert after[field] == before[field]


def test_event_requires_its_own_portfolio_effective_transaction(
    ledger_session: Session, trade: models.TradeEvent, monkeypatch: pytest.MonkeyPatch
) -> None:
    def absent_transaction(session: Session, portfolio_key: str) -> list[dict[str, JsonValue]]:
        return []

    monkeypatch.setattr(operations, "transaction_views", absent_transaction)
    with pytest.raises(ValueError):
        TradeMonitorService(ledger_session).list("TEST_BOOK")


def test_missing_nav_zero_and_signed_observations_keep_their_meaning(
    ledger_session: Session, risk: models.TradeRiskSnapshot
) -> None:
    risk.before = {"nav": None, "beta": None, "positions": [], "exposures": {}}
    risk.after = {
        "nav": "10000.00000000",
        "beta": "-0.12500000",
        "positions": [{"symbol": "AAA", "weight": "0.00000000"}],
        "exposures": {"sector": [{"name": "Test", "weight": "-0.05000000"}]},
        "as_of": "2026-01-06T23:59:59.999999+00:00",
    }
    ledger_session.commit()
    result = OBJECT.validate_python(TradeMonitorService(ledger_session).list("TEST_BOOK")[0])
    assert result["pre_beta"] is None and result["weight_before"] is None
    assert result["sector_weight_before"] is None
    assert result["post_beta"] == "-0.12500000"
    assert result["weight_after"] == "0.00000000"
    assert result["sector_weight_after"] == "-0.05000000"
    assert result["risk_as_of"] == risk.after["as_of"]
    json.dumps(result, allow_nan=False)


def test_empty_snapshots_and_absent_positions_are_not_conflated(
    ledger_session: Session, risk: models.TradeRiskSnapshot
) -> None:
    risk.before = {}
    risk.after = {"nav": "0", "positions": [], "exposures": {}}
    ledger_session.commit()
    result = OBJECT.validate_python(TradeMonitorService(ledger_session).list("TEST_BOOK")[0])
    assert result["weight_before"] is None and result["sector_weight_before"] is None
    assert result["weight_after"] == 0 and result["sector_weight_after"] == 0
    assert result["pre_beta"] is None and result["post_beta"] is None


def test_source_extensions_and_review_lifecycle_are_preserved(
    ledger_session: Session, trade: models.TradeEvent, risk: models.TradeRiskSnapshot
) -> None:
    extension: dict[str, JsonValue] = {"last": None, "first": 0, "nested": {"z": -1, "a": ""}}
    trade.payload = {**trade.payload, "demo_seed": True, "provider_extension": extension}
    breach: dict[str, JsonValue] = {
        "provider_extension": extension,
        "metric": "CONCENTRATION",
        "value": "0.2500",
        "threshold": "0.20",
        "severity": "WARN",
        "state": "OPEN",
    }
    risk.breaches = [breach]
    ledger_session.commit()
    service = TradeMonitorService(ledger_session)
    before = OBJECT.validate_python(service.list("TEST_BOOK")[0])
    assert before["provider_extension"] == extension and before["demo_seed"] is True
    assert before["breaches"] == [breach]
    assert json.dumps(before["breaches"]) == json.dumps([breach])
    reviewed = service.review(trade.id, "FLAGGED", "Fictional review receipt")
    assert reviewed == {"id": trade.id, "state": "FLAGGED", "note": "Fictional review receipt"}
    after = OBJECT.validate_python(service.list("TEST_BOOK")[0])
    assert after == {**before, "review_state": "FLAGGED"}
    assert len(ledger_session.scalars(select(models.TradeReview)).all()) == 1


def test_seed_style_event_without_risk_does_not_invent_measurements(
    ledger_session: Session, trade: models.TradeEvent, risk: models.TradeRiskSnapshot
) -> None:
    ledger_session.delete(risk)
    trade.payload = {"demo_seed": True, "thesis": "Fictional seed evidence"}
    ledger_session.commit()
    result = OBJECT.validate_python(TradeMonitorService(ledger_session).list("TEST_BOOK")[0])
    for key in ("pre_beta", "post_beta", "weight_before", "weight_after", "risk_as_of"):
        assert result[key] is None
    assert result["breaches"] == [] and result["demo_seed"] is True


def test_invalid_breach_values_do_not_reach_json_response(
    ledger_session: Session, risk: models.TradeRiskSnapshot
) -> None:
    risk.breaches = [{"metric": "X", "value": "NaN", "severity": "WARN", "state": "OPEN"}]
    ledger_session.commit()
    with pytest.raises(ValueError):
        TradeMonitorService(ledger_session).list("TEST_BOOK")
