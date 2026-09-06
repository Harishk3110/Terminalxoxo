"""Balance recognition, reversals, dated validation and honest incomplete NAVs."""

from decimal import Decimal as D
from typing import Any

import pytest
from app import models
from app.portfolio_api import router as legacy_router
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

BASE = "/api/v1/portfolios/book"


def adjustment(client: TestClient, **fields: Any) -> dict[str, Any]:
    response = client.post(
        BASE + "/balances",
        json={
            "effective_date": "2026-01-06",
            "bucket": "accrued_income",
            "currency": "SGD",
            "amount": "50",
            "reason": "Declared income accrual",
            **fields,
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


@pytest.mark.parametrize(
    "bucket,sign",
    [
        ("accrued_income", 1),
        ("receivables", 1),
        ("payables", -1),
        ("accrued_fees", -1),
        ("other_liabilities", -1),
    ],
)
def test_each_balance_bucket_changes_nav_and_persists_source_audit(
    client: TestClient,
    ledger_session: Session,
    bucket: str,
    sign: int,
) -> None:
    created = adjustment(client, bucket=bucket)
    data = client.get(BASE + "/summary?end=2026-01-06").json()
    assert D(data["portfolio"]["nav"]) == D("10000") + sign * D("50")
    assert data["reconciliation"]["state"] == "BALANCED"
    assert D(data["accounting"]["totals"][bucket]) == D("50")
    components = client.get(
        BASE + "/accounting", params={"run_id": data["valuation_run_id"]}
    ).json()["items"]
    component = next(row for row in components if row["adjustment_id"] == created["id"])
    assert component["category"] == ("ACCRUAL" if sign == 1 else "LIABILITY")
    assert component["provenance"]["reason"] == "Declared income accrual"
    audit = ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.resource_id == created["id"])
    )
    assert audit is not None
    assert audit.action == "NAV_BALANCE_ADJUSTED"
    assert audit.metadata_json["amount"] == "50"


def test_reversal_does_not_edit_original_adjustment_or_run(
    client: TestClient, ledger_session: Session
) -> None:
    first = adjustment(client)
    original = client.get(BASE + "/summary?end=2026-01-06").json()
    adjustment(
        client, amount="-20", effective_date="2026-01-07", reason="Partial accrual correction"
    )
    current = client.get(BASE + "/summary?end=2026-01-07").json()
    assert D(current["portfolio"]["nav"]) == D("10030")
    assert D(ledger_session.get(models.PortfolioBalanceAdjustment, first["id"]).amount) == D("50")
    old = client.get(BASE + "/accounting", params={"run_id": original["valuation_run_id"]}).json()
    assert D(old["totals"]["accrued_income"]) == D("50")
    assert len(client.get(BASE + "/balances").json()["items"]) == 2


def test_rejects_backdated_reversal_that_breaks_a_later_day(
    client: TestClient, ledger_session: Session
) -> None:
    adjustment(client, amount="50")
    adjustment(client, amount="-40", effective_date="2026-01-08", reason="Recognition reversal")
    before = ledger_session.scalar(select(func.count(models.AuditLog.id)))
    response = client.post(
        BASE + "/balances",
        json={
            "effective_date": "2026-01-07",
            "bucket": "accrued_income",
            "currency": "SGD",
            "amount": "-20",
            "reason": "Backdated reversal",
        },
    )
    assert response.status_code == 422
    assert "negative on 2026-01-08" in response.json()["detail"]
    assert len(client.get(BASE + "/balances").json()["items"]) == 2
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == before


def test_currency_buckets_cannot_offset_an_invalid_reversal(client: TestClient) -> None:
    adjustment(client, currency="USD", amount="100")
    response = client.post(
        BASE + "/balances",
        json={
            "effective_date": "2026-01-06",
            "bucket": "accrued_income",
            "currency": "SGD",
            "amount": "-20",
            "reason": "Incorrect currency reversal",
        },
    )
    assert response.status_code == 422
    assert "SGD negative" in response.json()["detail"]


def test_same_day_full_reversal_is_valid_and_keeps_both_rows(client: TestClient) -> None:
    adjustment(client)
    adjustment(client, amount="-50", reason="Full same day reversal")
    data = client.get(BASE + "/summary?end=2026-01-06").json()
    assert D(data["portfolio"]["nav"]) == D("10000")
    assert D(data["accounting"]["totals"]["accrued_income"]) == 0
    assert len([row for row in data["accounting"]["items"] if row["adjustment_id"]]) == 2


def test_effective_date_recognized_without_market_observation(client: TestClient) -> None:
    adjustment(client, effective_date="2026-01-10")
    data = client.get(BASE + "/summary?end=2026-01-12").json()
    curve = {row["date"]: row for row in data["curve"]}
    assert "2026-01-10" in curve
    assert D(str(curve["2026-01-10"]["daily_pnl"])) == D("50")
    assert curve["2026-01-12"]["daily_pnl"] == 0
    prior = client.get(BASE + "/summary?end=2026-01-09").json()
    assert D(prior["portfolio"]["nav"]) == D("10000")


def test_missing_fx_preserves_native_accrual_but_disables_nav(client: TestClient) -> None:
    adjustment(client, currency="JPY", amount="500")
    data = client.get(BASE + "/summary?end=2026-01-06").json()
    assert data["portfolio"]["nav"] is None
    assert data["quality"] == "UNAVAILABLE"
    assert data["accounting"]["totals"]["accrued_income"] is None
    rows = client.get(
        BASE + "/accounting", params={"run_id": data["valuation_run_id"], "category": "ACCRUAL"}
    ).json()["items"]
    assert D(rows[0]["native_amount"]) == D("500")
    assert rows[0]["base_amount"] is None


@pytest.mark.parametrize(
    "override",
    [
        {"amount": "0"},
        {"amount": "NaN"},
        {"amount": "Infinity"},
        {"amount": "0.000000001"},
        {"currency": "usd"},
        {"currency": "ABC"},
        {"reason": "     "},
        {"bucket": "cash"},
        {"effective_date": "2026-01-01"},
        {"effective_date": "2099-01-01"},
        {"amount": "-1"},
    ],
)
def test_invalid_adjustments_leave_no_partial_data(
    client: TestClient, ledger_session: Session, override: dict[str, str]
) -> None:
    before = ledger_session.scalar(select(func.count(models.AuditLog.id)))
    response = client.post(
        BASE + "/balances",
        json={
            "effective_date": "2026-01-06",
            "bucket": "accrued_income",
            "currency": "SGD",
            "amount": "50",
            "reason": "Declared income accrual",
            **override,
        },
    )
    assert response.status_code == 422, response.text
    assert client.get(BASE + "/balances").json()["items"] == []
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == before


def test_legacy_balance_endpoint_uses_same_validation_and_audit(
    client: TestClient, ledger_session: Session
) -> None:
    client.app.include_router(legacy_router)
    path = "/api/v1/operations/balances?portfolio=book"
    payload = {
        "effective_date": "2026-01-06",
        "bucket": "accrued_fees",
        "currency": "SGD",
        "amount": "10",
        "reason": "Unpaid custodian fee",
    }
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    invalid = client.post(path, json={**payload, "amount": "-20"})
    assert invalid.status_code == 422
    assert len(client.get(BASE + "/balances").json()["items"]) == 1
    assert (
        ledger_session.scalar(
            select(func.count(models.AuditLog.id)).where(
                models.AuditLog.action == "NAV_BALANCE_ADJUSTED"
            )
        )
        == 1
    )
