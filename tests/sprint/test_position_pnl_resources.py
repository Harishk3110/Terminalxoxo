"""Saved valuation integration for economic daily P&L and missing mark provenance."""

from datetime import UTC, datetime
from decimal import Decimal as D

from app import models
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

BASE = "/api/v1/portfolios/book"


def record(client: TestClient, **fields) -> dict:
    response = client.post(
        BASE + "/transactions", json={"trade_date": "2026-01-06", "symbol": "AAA", **fields}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_cash_merger_daily_attribution_ties_to_nav_and_saved_payload(
    client: TestClient, ledger_session: Session
) -> None:
    record(client, transaction_type="BUY", quantity="10", price="120")
    record(
        client,
        transaction_type="MERGER",
        trade_date="2026-01-07",
        child_symbol="BBB",
        metadata={"exchange_ratio": "1", "cash_per_share": "6", "cash_cost_allocation": ".05"},
    )
    summary = client.get(BASE + "/summary?end=2026-01-07").json()
    assert summary["calculation_version"] == "knk-nav-4.7"
    assert D(str(summary["portfolio"]["daily_pnl"])) == D(60)
    contributions = {row["symbol"]: row for row in summary["attribution"]}
    assert D(contributions["AAA"]["daily_pnl"]) == 0
    assert D(contributions["BBB"]["daily_pnl"]) == 60
    parent = contributions["AAA"]["daily_pnl_details"]
    child = contributions["BBB"]["daily_pnl_details"]
    assert D(parent["economic_cash"]) == 60
    assert D(parent["internal_transfer"]) == -1140
    assert D(child["internal_transfer"]) == 1140
    assert D(parent["pnl"]) + D(child["pnl"]) == D(str(summary["portfolio"]["daily_pnl"]))
    persisted = ledger_session.get(models.PortfolioValuationRun, summary["valuation_run_id"])
    assert persisted.payload["attribution"] == summary["attribution"]
    assert summary["positions"][0]["daily_pnl_details"] == child


def test_spinoff_avoids_reporting_internal_value_transfer_as_gain(
    client: TestClient, ledger_session: Session
) -> None:
    record(client, transaction_type="BUY", quantity="10", price="120")
    record(
        client,
        transaction_type="SPINOFF",
        trade_date="2026-01-07",
        quantity="2",
        child_symbol="BBB",
        metadata={"cost_allocation": ".2"},
    )
    price = ledger_session.scalar(
        select(models.MarketObservation).where(
            models.MarketObservation.instrument_id == "AAA",
            models.MarketObservation.timestamp == datetime(2026, 1, 7, 20, tzinfo=UTC),
        )
    )
    price.price = D(96)
    ledger_session.commit()
    summary = client.get(BASE + "/summary?end=2026-01-07").json()
    assert D(str(summary["portfolio"]["daily_pnl"])) == 0
    rows = {row["symbol"]: row for row in summary["positions"]}
    assert D(str(rows["AAA"]["daily_pnl"])) == 0
    assert D(str(rows["BBB"]["daily_pnl"])) == 0
    assert D(rows["AAA"]["daily_pnl_details"]["internal_transfer"]) == -240
    assert D(rows["BBB"]["daily_pnl_details"]["internal_transfer"]) == 240


def test_income_for_closed_position_is_in_daily_attribution(client: TestClient) -> None:
    record(client, transaction_type="BUY", quantity="10", price="120")
    record(client, transaction_type="SELL", quantity="10", price="120")
    record(client, transaction_type="DIVIDEND", trade_date="2026-01-07", amount="12", tax="2")
    summary = client.get(BASE + "/summary?end=2026-01-07").json()
    assert summary["positions"] == []
    assert D(str(summary["portfolio"]["daily_pnl"])) == 10
    assert D(summary["attribution"][0]["daily_pnl"]) == 10
    assert D(summary["attribution"][0]["daily_pnl_details"]["economic_cash"]) == 10


def test_missing_previous_mark_is_not_a_zero_opening_position_value(
    client: TestClient, ledger_session: Session
) -> None:
    ledger_session.execute(
        delete(models.MarketObservation).where(
            models.MarketObservation.instrument_id == "AAA",
            models.MarketObservation.timestamp < datetime(2026, 1, 7, tzinfo=UTC),
        )
    )
    ledger_session.commit()
    record(client, transaction_type="BUY", quantity="10", price="120")
    summary = client.get(BASE + "/summary?end=2026-01-07").json()
    row = summary["positions"][0]
    assert row["daily_pnl"] is None
    assert row["daily_pnl_details"]["opening_value"] is None
    assert D(row["daily_pnl_details"]["closing_value"]) == D(1200)
    assert row["daily_pnl_details"]["state"] == "UNAVAILABLE"
    assert "Opening position mark is unavailable" in row["daily_pnl_details"]["warnings"]
