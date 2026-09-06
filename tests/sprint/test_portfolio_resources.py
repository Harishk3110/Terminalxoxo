"""HTTP contracts for scoped resources, corrections, policy and atomic failures."""

from decimal import Decimal as D

import pytest
from app import models
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def buy(client: TestClient, quantity: str = "10") -> dict:
    response = client.post(
        "/api/v1/portfolios/book/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": quantity,
            "price": "100",
            "settle_date": "2026-01-08",
            "commission": "2",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_portfolio_list_and_metadata_are_backed_by_persisted_accounts(client: TestClient) -> None:
    response = client.get("/api/v1/portfolios")
    assert response.status_code == 200
    assert [row["code"] for row in response.json()["items"]] == ["TEST_BOOK"]
    metadata = client.get("/api/v1/portfolios/book").json()
    assert metadata["accounts"][0]["id"] == "account"
    assert metadata["accounting_policy"] == {
        "method": "AVERAGE",
        "capitalize_commissions": False,
        "capitalize_fees": False,
    }
    assert client.get("/api/v1/portfolios/TEST_BOOK").json()["id"] == "book"


def test_unknown_portfolio_is_404_not_an_unscoped_fallback(client: TestClient) -> None:
    response = client.get("/api/v1/portfolios/unknown")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_creation_posts_explicit_opening_capital_and_audits(
    client: TestClient, ledger_session: Session
) -> None:
    response = client.post(
        "/api/v1/portfolios",
        json={
            "code": "NEW_BOOK",
            "name": "New ledger",
            "reference_capital": "70000",
            "opening_date": "2026-01-05",
            "method": "FIFO",
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["code"] == "NEW_BOOK"
    assert created["is_demo"] is False
    assert created["is_default"] is False
    assert created["accounting_policy"]["method"] == "FIFO"
    assert created["accounting_policy"]["capitalize_commissions"] is True
    txns = client.get(f"/api/v1/portfolios/{created['id']}/transactions").json()["items"]
    assert len(txns) == 1
    assert txns[0]["type"] == "DEPOSIT"
    assert D(txns[0]["gross_amount"]) == D("70000")
    assert txns[0]["account_id"] == created["accounts"][0]["id"]
    assert (
        ledger_session.scalar(
            select(func.count(models.AuditLog.id)).where(
                models.AuditLog.action == "PORTFOLIO_CREATED"
            )
        )
        == 1
    )


def test_duplicate_code_rolls_back_portfolio_account_and_capital(
    client: TestClient, ledger_session: Session
) -> None:
    before = ledger_session.scalar(select(func.count(models.Portfolio.id)))
    response = client.post(
        "/api/v1/portfolios",
        json={
            "code": "TEST_BOOK",
            "name": "Duplicate",
            "reference_capital": "1000",
            "opening_date": "2026-01-05",
        },
    )
    assert response.status_code == 409
    assert ledger_session.scalar(select(func.count(models.Portfolio.id))) == before
    assert ledger_session.scalar(select(func.count(models.PortfolioTransaction.id))) == 1
    assert ledger_session.scalar(select(func.count(models.PortfolioAccount.id))) == 1


@pytest.mark.parametrize(
    "override",
    [
        {"reference_capital": "0"},
        {"reference_capital": "NaN"},
        {"base_currency": "XYZ"},
        {"benchmark": "MISSING"},
        {"code": "KNK_MAIN"},
        {"opening_date": "2099-01-01"},
        {"name": "  "},
    ],
)
def test_invalid_portfolio_creation_never_persists_partial_records(
    client: TestClient, ledger_session: Session, override: dict[str, str]
) -> None:
    payload = {
        "code": "NEW_BOOK",
        "name": "New book",
        "reference_capital": "1000",
        "opening_date": "2026-01-05",
        **override,
    }
    response = client.post("/api/v1/portfolios", json=payload)
    assert response.status_code == 422
    assert ledger_session.scalar(select(func.count(models.Portfolio.id))) == 1
    assert ledger_session.scalar(select(func.count(models.PortfolioAccount.id))) == 1


def test_settlement_fields_and_nav_are_consistent_before_and_after_settlement(
    client: TestClient,
) -> None:
    buy(client)
    before = client.get("/api/v1/portfolios/book/cash?end=2026-01-07").json()
    after = client.get("/api/v1/portfolios/book/cash?end=2026-01-09").json()
    cash_before = before["items"][0]
    assert D(cash_before["settled"]) == D("10000")
    assert D(cash_before["payable"]) == D("1002")
    assert D(cash_before["available"]) == D("8998")
    assert D(after["items"][0]["settled"]) == D("8998")
    assert before["portfolio"]["nav"] == after["portfolio"]["nav"] == "10198.00"
    assert after["portfolio"]["settlement_payables"] == "0.00"


def test_position_detail_exposes_scoped_lots_and_immutable_run_id(client: TestClient) -> None:
    transaction = buy(client)
    response = client.get("/api/v1/portfolios/book/positions/AAA?end=2026-01-09")
    assert response.status_code == 200, response.text
    data = response.json()
    assert D(data["quantity"]) == D("10")
    assert data["lots"][0]["entry_id"] == transaction["id"]
    assert data["valuation_run_id"]
    assert data["matches"] == []
    assert client.get("/api/v1/portfolios/book/positions/BBB?end=2026-01-09").status_code == 404


def test_amendment_http_contract_versions_and_replay(client: TestClient) -> None:
    transaction = buy(client)
    url = f"/api/v1/portfolios/book/transactions/{transaction['id']}"
    corrected = client.put(
        url,
        json={
            "expected_version": 1,
            "reason": "Correct confirmed quantity",
            "changes": {"quantity": "8"},
        },
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["audit_version"] == 2
    detail = client.get(url).json()
    assert D(detail["quantity"]) == D("8")
    assert len(detail["revisions"]) == 1
    assert D(detail["revisions"][0]["before"]["entry"]["quantity"]) == D("10")
    stale = client.put(
        url,
        json={
            "expected_version": 1,
            "reason": "Stale editor quantity",
            "changes": {"quantity": "7"},
        },
    )
    assert stale.status_code == 409
    assert D(client.get(url).json()["quantity"]) == D("8")


def test_delete_records_void_with_explicit_reason_and_no_physical_deletion(
    client: TestClient, ledger_session: Session
) -> None:
    transaction = buy(client)
    url = f"/api/v1/portfolios/book/transactions/{transaction['id']}"
    response = client.request(
        "DELETE", url, json={"expected_version": 1, "reason": "Duplicate internal booking"}
    )
    assert response.status_code == 200
    assert response.json()["ledger_state"] == "VOID"
    assert client.get(url).json()["ledger_state"] == "VOID"
    assert ledger_session.get(models.PortfolioTransaction, transaction["id"]) is not None
    summary = client.get("/api/v1/portfolios/book/summary?end=2026-01-09").json()
    assert summary["positions"] == []
    assert summary["portfolio"]["nav"] == "10000.00"


@pytest.mark.parametrize(
    "changes",
    [{"id": "replacement"}, {"currency": "USD"}, {"account_id": "different"}, {"quantity": None}],
)
def test_immutable_fields_and_null_accounting_changes_are_rejected(
    client: TestClient, changes: dict
) -> None:
    transaction = buy(client)
    url = f"/api/v1/portfolios/book/transactions/{transaction['id']}"
    response = client.put(
        url, json={"expected_version": 1, "reason": "Test invalid modification", "changes": changes}
    )
    assert response.status_code == 422
    assert client.get(url).json()["audit_version"] == 1


def test_policy_api_requires_reason_and_strict_boolean_switches(client: TestClient) -> None:
    url = "/api/v1/portfolios/book/accounting-policy"
    request = {
        "method": "FIFO",
        "capitalize_commissions": True,
        "capitalize_fees": False,
        "reason": "Adopt FIFO lot matching",
    }
    invalid = client.put(url, json={**request, "capitalize_commissions": "true"})
    assert invalid.status_code == 422
    valid = client.put(url, json=request)
    assert valid.status_code == 200, valid.text
    assert valid.json()["accounting_policy"]["method"] == "FIFO"
    assert client.put(url, json=request).status_code == 422


@pytest.mark.parametrize("endpoint", ["value", "recalculate"])
def test_explicit_recalculation_creates_run_and_audit(
    client: TestClient, ledger_session: Session, endpoint: str
) -> None:
    buy(client)
    response = client.post(f"/api/v1/portfolios/book/{endpoint}?end=2026-01-09")
    assert response.status_code == 200, response.text
    run_id = response.json()["valuation_run_id"]
    audit = ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.action == "PORTFOLIO_RECALCULATED")
    )
    assert audit is not None
    assert audit.metadata_json["valuation_run_id"] == run_id
    assert ledger_session.get(models.PortfolioValuationRun, run_id) is not None


def test_future_valuation_and_non_demo_reset_are_rejected(client: TestClient) -> None:
    assert client.get("/api/v1/portfolios/book/summary?end=2099-01-01").status_code == 422
    response = client.post(
        "/api/v1/portfolios/book/reset-demo", json={"confirmation": "RESET KNK_MAIN DEMO"}
    )
    assert response.status_code == 422


def test_nav_performance_attribution_share_the_same_ledger(client: TestClient) -> None:
    buy(client)
    nav = client.get("/api/v1/portfolios/book/nav?end=2026-01-09").json()
    attribution = client.get("/api/v1/portfolios/book/attribution?end=2026-01-09").json()
    performance = client.get("/api/v1/portfolios/book/performance?end=2026-01-09").json()
    assert nav["valuation_run_id"] == attribution["valuation_run_id"]
    assert nav["reconciliation"]["state"] == "BALANCED"
    assert D(attribution["items"][0]["total_pnl"]) == D("198")
    assert performance["metrics"]["twr"] == pytest.approx(0.0198)
    assert performance["metrics"]["cagr"] is None
