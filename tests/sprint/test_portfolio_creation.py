"""Creation options, exact opening capital and isolated ledger ownership."""

from datetime import UTC, datetime
from decimal import Decimal as D

import pytest
from app import models
from app.portfolio_operations import CURRENCIES
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def creation_payload(**changes: object) -> dict[str, object]:
    return {
        "code": "RESEARCH_BOOK",
        "name": " Research allocation ",
        "reference_capital": "1000.12345678",
        "opening_date": "2026-01-05",
        "benchmark": "SPY",
        "method": "FIFO",
        "allow_short": True,
        "capitalize_commissions": False,
        "capitalize_fees": True,
        **changes,
    }


def counts(session: Session) -> dict[str, int]:
    return {
        model.__tablename__: session.scalar(select(func.count(model.id))) or 0
        for model in (
            models.Portfolio,
            models.PortfolioProfile,
            models.PortfolioAccount,
            models.PortfolioTransaction,
            models.TransactionDetail,
            models.AuditLog,
        )
    }


def test_creation_options_use_configured_master_without_requiring_knk_main(
    client: TestClient,
) -> None:
    before = datetime.now(UTC).date().isoformat()
    response = client.get("/api/v1/portfolios/creation-options")
    assert response.status_code == 200, response.text
    options = response.json()
    assert options["currencies"] == sorted(CURRENCIES)
    assert set(options["methods"]) == {"AVERAGE", "FIFO"}
    assert options["max_opening_date"] in {before, datetime.now(UTC).date().isoformat()}
    assert options["date_boundary"] == "UTC"
    assert D(options["maximum_capital"]) == D("1e12")
    assert options["capital_decimal_places"] == 8
    assert options["benchmarks"] == [
        {"symbol": "AAA", "name": "Test AAA", "currency": "SGD"},
        {"symbol": "BBB", "name": "Test BBB", "currency": "SGD"},
        {"symbol": "SPY", "name": "Test SPY", "currency": "USD"},
    ]
    assert [row["code"] for row in client.get("/api/v1/portfolios").json()["items"]] == [
        "TEST_BOOK"
    ]


def test_created_metadata_and_actual_deposit_agree_after_expiring_session(
    client: TestClient, ledger_session: Session
) -> None:
    ledger_session.expire_all()
    original = client.get("/api/v1/portfolios/book").json()
    response = client.post("/api/v1/portfolios", json=creation_payload())
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    ledger_session.expire_all()
    record = client.get(f"/api/v1/portfolios/{identifier}").json()
    assert record["name"] == "Research allocation"
    assert D(record["reference_capital"]) == D("1000.12345678")
    assert record["configuration"]["opening_date"] == "2026-01-05"
    assert record["configuration"]["execution_mode"] == "MANUAL"
    assert record["configuration"]["allow_short"] is True
    assert record["accounting_policy"] == {
        "method": "FIFO",
        "capitalize_commissions": False,
        "capitalize_fees": True,
    }
    assert record["is_default"] is False
    assert record["is_demo"] is False
    assert record["accounts"][0]["provider"] is None
    rows = client.get(f"/api/v1/portfolios/{identifier}/transactions").json()["items"]
    assert len(rows) == 1
    assert rows[0]["type"] == "DEPOSIT"
    assert rows[0]["portfolio_id"] == identifier
    assert rows[0]["account_id"] == record["accounts"][0]["id"]
    assert D(rows[0]["net_amount"]) == D(record["reference_capital"])
    assert client.get("/api/v1/portfolios/book").json() == original
    actions = ledger_session.scalars(
        select(models.AuditLog).where(models.AuditLog.resource_id == identifier)
    ).all()
    assert [row.action for row in actions] == ["PORTFOLIO_CREATED"]
    assert actions[0].metadata_json["code"] == "RESEARCH_BOOK"


@pytest.mark.parametrize(
    "capital",
    [
        "0.000000001",
        "1000.123456789",
        "999999999999.12345678",
        "1000000000000.01",
        "Infinity",
        "-5",
    ],
)
def test_unsafe_opening_capital_never_leaves_partial_ledger_or_audit(
    client: TestClient, ledger_session: Session, capital: str
) -> None:
    before = counts(ledger_session)
    response = client.post("/api/v1/portfolios", json=creation_payload(reference_capital=capital))
    assert response.status_code == 422, response.text
    assert counts(ledger_session) == before
    assert client.get("/api/v1/portfolios/RESEARCH_BOOK").status_code == 404


def test_duplicate_retry_keeps_one_opening_deposit_and_one_creation_audit(
    client: TestClient, ledger_session: Session
) -> None:
    payload = creation_payload()
    assert client.post("/api/v1/portfolios", json=payload).status_code == 201
    before = counts(ledger_session)
    retry = client.post("/api/v1/portfolios", json=payload)
    assert retry.status_code == 409
    assert counts(ledger_session) == before


def test_selected_ledger_mutations_and_valuations_do_not_change_original_book(
    client: TestClient,
) -> None:
    main = client.get("/api/v1/portfolios/book/summary?end=2026-01-07").json()
    response = client.post("/api/v1/portfolios", json=creation_payload(base_currency="USD"))
    assert response.status_code == 201, response.text
    key = response.json()["id"]
    traded = client.post(
        f"/api/v1/portfolios/{key}/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "SPY",
            "quantity": "2",
            "price": "100",
            "fx_rate_to_base": "1",
        },
    )
    assert traded.status_code == 201, traded.text
    transaction = traded.json()
    summary = client.get(f"/api/v1/portfolios/{key}/summary?end=2026-01-07").json()
    assert summary["portfolio"]["base_currency"] == "USD"
    assert D(summary["portfolio"]["nav"]) == D("1040.12")
    assert summary["positions"][0]["instrument_id"] == "SPY"
    assert (
        client.get(f"/api/v1/portfolios/book/transactions/{transaction['id']}").status_code == 404
    )
    revised = client.put(
        f"/api/v1/portfolios/{key}/transactions/{transaction['id']}",
        json={
            "expected_version": 1,
            "reason": "Correct selected book consideration",
            "changes": {"price": "110"},
        },
    )
    assert revised.status_code == 200, revised.text
    after = client.get(f"/api/v1/portfolios/{key}/summary?end=2026-01-07").json()
    assert D(after["portfolio"]["nav"]) == D("1020.12")
    unchanged = client.get("/api/v1/portfolios/book/summary?end=2026-01-07").json()
    assert unchanged["portfolio"]["nav"] == main["portfolio"]["nav"]
    assert unchanged["transactions"] == main["transactions"]
    assert unchanged["positions"] == []


@pytest.mark.parametrize(
    "field", ["method", "capitalize_commissions", "capitalize_fees", "allow_short"]
)
def test_creation_rejects_unsupported_or_coerced_policy_settings(
    client: TestClient, ledger_session: Session, field: str
) -> None:
    before = counts(ledger_session)
    response = client.post("/api/v1/portfolios", json=creation_payload(**{field: "false"}))
    assert response.status_code == 422
    assert counts(ledger_session) == before
