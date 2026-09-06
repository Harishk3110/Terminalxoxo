"""Subledger persistence, portfolio scoping and immutable historical run queries."""

from datetime import date
from decimal import Decimal as D
from typing import Any

from app import models
from app.accounting_persistence import accounting_records
from app.portfolio_valuation import PortfolioValuationService
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

BASE = "/api/v1/portfolios/book"


def transaction(client: TestClient, **fields: Any) -> dict[str, Any]:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": "10",
            "price": "100",
            "commission": "2",
            **fields,
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_summary_materializes_capital_and_fee_source_records(
    client: TestClient, ledger_session: Session
) -> None:
    trade = transaction(client)
    summary = client.get(BASE + "/summary?end=2026-01-06").json()
    response = client.get(BASE + "/accounting", params={"run_id": summary["valuation_run_id"]})
    assert response.status_code == 200, response.text
    detail = response.json()
    assert detail["state"] == "AVAILABLE"
    assert detail["reconciliation"]["state"] == "BALANCED"
    assert D(detail["totals"]["external_flows"]) == D("10000")
    assert D(detail["totals"]["expensed_fees"]) == D("2")
    assert {row["category"] for row in detail["items"]} == {"CAPITAL", "FEE"}
    fee = ledger_session.scalar(
        select(models.PortfolioFee).where(
            models.PortfolioFee.valuation_run_id == summary["valuation_run_id"]
        )
    )
    assert fee is not None
    assert fee.transaction_id == trade["id"]
    assert fee.account_id == "account"
    assert fee.instrument_id == "AAA"
    assert fee.native_amount == D("2")
    assert fee.payload["key"] == f"{trade['id']}:COMMISSION"


def test_latest_accounting_endpoint_returns_normalized_records(
    client: TestClient, ledger_session: Session
) -> None:
    data = client.get(BASE + "/accounting").json()
    assert data["state"] == "AVAILABLE"
    assert len(data["items"]) == 1
    persisted = ledger_session.get(models.CapitalFlow, data["items"][0]["id"])
    assert persisted is not None
    assert persisted.valuation_run_id == data["valuation_run_id"]
    assert persisted.portfolio_id == "book"
    assert persisted.transaction_id == "deposit"


def test_policy_change_creates_new_components_without_rewriting_old_run(
    client: TestClient, ledger_session: Session
) -> None:
    transaction(client, fee="3", tax="1")
    old = client.get(BASE + "/summary?end=2026-01-06").json()
    old_id = old["valuation_run_id"]
    old_records = client.get(BASE + "/accounting", params={"run_id": old_id}).json()
    response = client.put(
        BASE + "/accounting-policy",
        json={
            "method": "FIFO",
            "capitalize_commissions": True,
            "capitalize_fees": True,
            "reason": "Capitalize trade costs under new policy",
        },
    )
    assert response.status_code == 200, response.text
    new = client.get(BASE + "/summary?end=2026-01-06").json()
    assert new["valuation_run_id"] != old_id
    assert new["portfolio"]["nav"] == old["portfolio"]["nav"]
    assert D(new["accounting"]["totals"]["capitalized_charges"]) == D("5")
    assert D(new["accounting"]["totals"]["expensed_fees"]) == 0
    assert D(new["accounting"]["totals"]["taxes"]) == 1
    assert client.get(BASE + "/accounting", params={"run_id": old_id}).json() == old_records
    assert ledger_session.scalar(select(func.count(models.PortfolioFee.id))) == 6


def test_pending_settlement_liability_expires_in_next_run_only(
    client: TestClient, ledger_session: Session
) -> None:
    trade = transaction(client, settle_date="2026-01-08")
    pending = client.get(BASE + "/summary?end=2026-01-06").json()
    settled = client.get(BASE + "/summary?end=2026-01-08").json()
    first = accounting_records(ledger_session, "book", pending["valuation_run_id"])
    last = accounting_records(ledger_session, "book", settled["valuation_run_id"])
    liabilities = [row for row in first if row["category"] == "LIABILITY"]
    assert len(liabilities) == 2
    assert sum((D(row["base_amount"]) for row in liabilities), D("0")) == D("1002")
    assert {row["transaction_id"] for row in liabilities} == {trade["id"]}
    assert all(row["settlement_date"] == "2026-01-08" for row in liabilities)
    assert not [row for row in last if row["category"] == "LIABILITY"]
    assert pending["portfolio"]["nav"] == settled["portfolio"]["nav"]
    assert ledger_session.scalar(select(func.count(models.PortfolioLiability.id))) == 2


def test_income_and_tax_records_retain_native_and_transaction_fx(client: TestClient) -> None:
    transaction(
        client,
        transaction_type="DIVIDEND",
        symbol="SPY",
        quantity="0",
        price="0",
        currency="USD",
        amount="10",
        tax="3",
        commission="0",
        fx_rate_to_base="1.25",
    )
    data = client.get(BASE + "/summary?end=2026-01-06").json()
    income = client.get(
        BASE + "/accounting", params={"run_id": data["valuation_run_id"], "category": "INCOME"}
    ).json()
    assert len(income["items"]) == 1
    assert D(income["items"][0]["native_amount"]) == D("10")
    assert D(income["items"][0]["base_amount"]) == D("12.5")
    assert D(income["totals"]["taxes"]) == D("3.75")
    assert income["category"] == "INCOME"


def test_voided_transaction_disappears_from_new_subledger_without_deleting_history(
    client: TestClient,
) -> None:
    fee = transaction(
        client,
        transaction_type="FEE",
        symbol=None,
        quantity="0",
        price="0",
        amount="9",
        commission="0",
    )
    original = client.get(BASE + "/summary?end=2026-01-06").json()
    response = client.request(
        "DELETE",
        BASE + f"/transactions/{fee['id']}",
        json={"expected_version": 1, "reason": "Duplicate fee entry removed"},
    )
    assert response.status_code == 200, response.text
    corrected = client.get(BASE + "/summary?end=2026-01-06").json()
    assert D(corrected["portfolio"]["nav"]) - D(original["portfolio"]["nav"]) == D("9")
    assert not [row for row in corrected["accounting"]["items"] if row["category"] == "FEE"]
    old = client.get(
        BASE + "/accounting", params={"run_id": original["valuation_run_id"], "category": "FEE"}
    ).json()
    assert len(old["items"]) == 1
    assert old["items"][0]["transaction_id"] == fee["id"]


def test_historical_run_scope_does_not_leak_other_portfolios(
    client: TestClient, ledger_session: Session
) -> None:
    summary = client.get(BASE + "/summary?end=2026-01-06").json()
    other = client.post(
        "/api/v1/portfolios",
        json={
            "code": "OTHER",
            "name": "Other book",
            "reference_capital": "50",
            "opening_date": "2026-01-05",
        },
    ).json()
    response = client.get(
        f"/api/v1/portfolios/{other['id']}/accounting",
        params={"run_id": summary["valuation_run_id"]},
    )
    assert response.status_code == 404
    assert accounting_records(ledger_session, other["id"], summary["valuation_run_id"]) == []
    assert client.get(BASE + "/accounting?run_id=unknown").status_code == 404
    assert client.get(BASE + "/accounting?category=orders").status_code == 422


def test_pre_subledger_historical_run_is_explicitly_unavailable(
    client: TestClient, ledger_session: Session
) -> None:
    ledger_session.add(
        models.PortfolioValuationRun(
            id="legacy-run",
            portfolio_id="book",
            fingerprint="legacy",
            valuation_date=date(2026, 1, 5),
            status="SUCCEEDED",
            nav=D("10000"),
            payload={"calculation_version": "legacy"},
        )
    )
    ledger_session.commit()
    response = client.get(BASE + "/accounting?run_id=legacy-run")
    assert response.status_code == 200
    assert response.json()["state"] == "UNAVAILABLE"
    assert response.json()["items"] == []
    assert "predates" in response.json()["warnings"][0]


def test_failed_persistence_rolls_back_run_and_components(ledger_session: Session) -> None:
    before = ledger_session.scalar(select(func.count(models.PortfolioValuationRun.id)))
    result = PortfolioValuationService(ledger_session).latest(
        "book", end=date(2026, 1, 6), force=True, commit=False
    )
    assert accounting_records(ledger_session, "book", result["valuation_run_id"])
    ledger_session.rollback()
    assert ledger_session.scalar(select(func.count(models.PortfolioValuationRun.id))) == before
    assert ledger_session.scalar(select(func.count(models.CapitalFlow.id))) == 0
