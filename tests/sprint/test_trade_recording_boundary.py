"""New ledger writes must not create evidence the trade monitor cannot read."""

import json
from decimal import Decimal

import pytest
from app import models
from app.portfolio_operations import PortfolioLedgerService, TradeMonitorService
from app.trade_monitor_contracts import trade_risk_snapshot
from fastapi.testclient import TestClient
from pydantic import JsonValue, TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.orm import Session

OBJECT = TypeAdapter(dict[str, JsonValue])


def test_no_prior_valuation_retains_the_existing_opening_snapshot() -> None:
    assert trade_risk_snapshot(None) == {"nav": "0", "beta": None, "positions": [], "exposures": {}}


def test_resource_api_rejects_invalid_rationale_then_accepts_a_valid_record(
    client: TestClient, ledger_session: Session
) -> None:
    payload = {
        "transaction_type": "BUY",
        "trade_date": "2026-01-06",
        "symbol": "AAA",
        "quantity": "1",
        "price": "120",
        "metadata": {"rationale": {"bad": "not text"}},
    }
    response = client.post("/api/v1/portfolios/book/transactions", json=payload)
    assert response.status_code == 422
    assert ledger_session.scalar(select(func.count(models.PortfolioTransaction.id))) == 1
    response = client.post(
        "/api/v1/portfolios/book/transactions",
        json={**payload, "metadata": {"rationale": "A valid fictional rationale"}},
    )
    assert response.status_code == 201
    assert ledger_session.scalar(select(func.count(models.PortfolioTransaction.id))) == 2
    assert len(TradeMonitorService(ledger_session).list("TEST_BOOK")) == 1


def test_recording_requires_the_calculated_position_weight_field() -> None:
    with pytest.raises(ValueError):
        trade_risk_snapshot(
            {
                "portfolio": {"nav": "100", "cash": "100"},
                "risk": {},
                "positions": [{"symbol": "AAA"}],
                "exposures": {},
                "as_of": "2026-01-06T23:59:59.999999+00:00",
            }
        )


@pytest.mark.parametrize("value", [True, False, 0, 1, [], {"note": "not text"}])
def test_invalid_rationale_is_rejected_before_any_ledger_write(
    ledger_session: Session, value: JsonValue
) -> None:
    with pytest.raises(ValueError):
        PortfolioLedgerService(ledger_session).add(
            {
                "transaction_type": "BUY",
                "trade_date": "2026-01-06",
                "symbol": "AAA",
                "quantity": "1",
                "price": "120",
                "metadata": {"rationale": value},
            },
            "TEST_BOOK",
        )
    # Deliberately inspect before rollback: invalid input must not insert rows.
    assert ledger_session.scalar(select(func.count(models.PortfolioTransaction.id))) == 1
    assert ledger_session.scalar(select(func.count(models.TransactionDetail.id))) == 1
    assert ledger_session.scalar(select(func.count(models.TradeEvent.id))) == 0
    assert ledger_session.scalar(select(func.count(models.TradeRiskSnapshot.id))) == 0
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == 0


@pytest.mark.parametrize("rationale", [None, "", "A recorded investment rationale"])
def test_valid_rationale_fallback_and_all_exposure_dimensions_are_preserved(
    ledger_session: Session, rationale: str | None
) -> None:
    result = PortfolioLedgerService(ledger_session).add(
        {
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": "1.25000000",
            "price": "120.00000000",
            "notes": "Recorded notes fallback",
            "metadata": {"rationale": rationale},
        },
        "TEST_BOOK",
    )
    ledger_session.commit()
    event = ledger_session.get(models.TradeEvent, result["trade_event_id"])
    assert event is not None
    assert event.payload["rationale"] == (rationale or "Recorded notes fallback")
    risk = ledger_session.scalar(
        select(models.TradeRiskSnapshot).where(models.TradeRiskSnapshot.trade_id == event.id)
    )
    assert risk is not None
    before = OBJECT.validate_python(risk.before, strict=True)
    after = OBJECT.validate_python(risk.after, strict=True)
    groups = OBJECT.validate_python(after["exposures"], strict=True)
    assert list(groups) == ["sector", "country", "currency", "asset_class", "industry"]
    sector = groups["sector"]
    assert isinstance(sector, list) and len(sector) == 1
    exposure = OBJECT.validate_python(sector[0], strict=True)
    assert exposure["name"] == "Test"
    assert exposure["known_value"] == "150.0000000000000000"
    assert exposure["position_count"] == 1
    assert exposure["missing_count"] == 0
    assert list(before) == list(after)
    assert list(after) == [
        "nav",
        "cash",
        "beta",
        "gross_exposure",
        "positions",
        "exposures",
        "as_of",
    ]
    json.dumps(after, allow_nan=False)
    monitor = TradeMonitorService(ledger_session).list("TEST_BOOK")
    assert len(monitor) == 1
    assert monitor[0]["weight_after"] is not None
    assert Decimal(str(monitor[0]["weight_after"])) == Decimal("0.015")
