"""Broker presentation cannot inherit internal financial components or run identities."""

from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal as D
from types import SimpleNamespace

import pytest
from app import broker_api
from sqlalchemy.orm import Session


def internal_snapshot() -> dict:
    return {
        "portfolio": {
            "id": "book",
            "code": "TEST_BOOK",
            "name": "Test book",
            "base_currency": "SGD",
            "execution_mode": "MANUAL",
            "broker_mode": "PAPER",
            "nav": "10000",
            "cash": "9000",
            "settled_cash": "9001",
            "available_cash": "8900",
            "reference_capital": "10000",
            "new_internal_measure": "PRIVATE INTERNAL AMOUNT",
        },
        "performance": {"twr": 0.1},
        "risk": {"beta": 1.25},
        "transactions": [{"id": "internal-transaction"}],
        "lots": [{"id": "internal-lot"}],
        "accounting": {"totals": {"fees_paid": "50"}},
        "exposure_balances": [{"bucket": "accrued_fees", "base_value": "-10"}],
        "exposure_methodology": "Internal economic cash",
        "valuation_run_id": "internal-run",
        "calculation_version": "knk-nav-4.5",
        "calculated_at": "2026-01-07T00:00:00Z",
        "new_internal_top_level": {"amount": "CONFIDENTIAL INTERNAL MEASURE"},
    }


def reported_snapshot() -> SimpleNamespace:
    return SimpleNamespace(
        id="paper-snapshot",
        currency="SGD",
        nav=D("700"),
        source="IBKR PAPER",
        as_of=datetime(2026, 1, 7, tzinfo=UTC),
        payload={
            "cash": [{"currency": "SGD", "amount": "100"}],
            "positions": [
                {
                    "symbol": "AAA",
                    "currency": "SGD",
                    "quantity": "5",
                    "market_price": "120",
                    "multiplier": "1",
                    "average_cost": "110",
                }
            ],
            "fx": {},
        },
    )


def test_connected_view_does_not_leak_existing_or_future_internal_fields(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    internal = internal_snapshot()
    before = deepcopy(internal)
    monkeypatch.setattr(broker_api, "current_snapshot", lambda *_: (reported_snapshot(), True))
    data = broker_api.account_view(ledger_session, internal)
    assert data["portfolio"]["nav"] == "700"
    assert D(data["portfolio"]["cash"]) == 100
    assert D(data["portfolio"]["market_value"]) == 600
    assert data["portfolio"]["view"] == "BROKER REPORTED"
    assert data["portfolio"]["settled_cash"] is data["portfolio"]["available_cash"] is None
    assert data["portfolio"]["reference_capital"] is None
    assert "new_internal_measure" not in data["portfolio"]
    assert "new_internal_top_level" not in data
    assert data["transactions"] == data["lots"] == data["lot_matches"] == []
    assert data["accounting"]["state"] == "UNAVAILABLE"
    assert data["accounting"]["totals"] is None
    assert data["cost_basis"] is None
    assert data["exposure_balances"] == []
    assert data["exposure_methodology"] is None
    assert data["valuation_run_id"] is None
    assert data["calculation_version"] == "BROKER SNAPSHOT"
    assert data["calculated_at"] is None
    assert data["performance"]["twr"] is data["risk"]["beta"] is None
    assert data["reconciliation"]["internal_nav"] == "10000"
    assert data["reconciliation"]["broker_nav"] == "700"
    assert data["broker_snapshot_id"] == "paper-snapshot"
    assert internal == before


def test_disconnected_view_remains_explicitly_internal_without_altering_snapshot(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    internal = internal_snapshot()
    monkeypatch.setattr(broker_api, "current_snapshot", lambda *_: (None, False))
    data = broker_api.account_view(ledger_session, internal)
    assert data["account_source"] == "INTERNAL LEDGER"
    assert data["broker_state"] == "NOT CONNECTED"
    assert data["portfolio"]["nav"] == "10000"
    assert data["valuation_run_id"] == "internal-run"
    assert data["exposure_balances"] == internal["exposure_balances"]
    monkeypatch.setattr(broker_api, "current_snapshot", lambda *_: (reported_snapshot(), False))
    offline = broker_api.account_view(ledger_session, internal)
    assert offline["broker_state"] == "STALE / OFFLINE"
    assert offline["account_source"] == "INTERNAL LEDGER"
    assert offline["portfolio"]["nav"] == "10000"
