from datetime import UTC, datetime, timedelta

import pytest
from app import models
from app.auth_guards import check_login_limit, origin_allowed
from app.services import DemoIngestionService
from app.worker_health import worker_state
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_persisted_login_limit_and_expiry(ledger_session: Session) -> None:
    for _ in range(10):
        ledger_session.add(
            models.LoginAttempt(
                email="account@example.invalid", success=False, ip_address="127.0.0.1"
            )
        )
    ledger_session.commit()
    with pytest.raises(HTTPException) as error:
        check_login_limit(ledger_session, "account@example.invalid", "127.0.0.1")
    assert error.value.status_code == 429
    check_login_limit(ledger_session, "different@example.invalid", "127.0.0.1")
    for row in ledger_session.scalars(select(models.LoginAttempt)):
        row.created_at = datetime.now(UTC) - timedelta(minutes=16)
    ledger_session.commit()
    check_login_limit(ledger_session, "account@example.invalid", "127.0.0.1")


def test_mutation_origin_protection() -> None:
    allowed = ["http://127.0.0.1:3001"]
    assert origin_allowed("POST", allowed[0], "same-origin", allowed)
    assert origin_allowed("POST", None, None, allowed)
    assert not origin_allowed("POST", "https://untrusted.example", None, allowed)
    assert not origin_allowed("POST", None, "cross-site", allowed)


def test_global_reset_never_deletes_user_records(ledger_session: Session) -> None:
    before = ledger_session.scalar(select(func.count()).select_from(models.PortfolioTransaction))
    with pytest.raises(ValueError, match="Destructive global reset"):
        DemoIngestionService(ledger_session).seed(reset=True)
    assert (
        ledger_session.scalar(select(func.count()).select_from(models.PortfolioTransaction))
        == before
    )


def test_worker_health_expires_and_does_not_infer_running_from_job_state(
    ledger_session: Session,
) -> None:
    run = models.AnalysisRun(
        id="worker-test", kind="backtest", name="Test", status="RUNNING", parameters={}, history=[]
    )
    ledger_session.add(run)
    ledger_session.commit()
    assert worker_state(ledger_session, [run])["state"] == "UNVERIFIED"
    beat = models.SystemHealthSnapshot(
        component="analytical-worker:worker-test", state="RUNNING", checked_at=datetime.now(UTC)
    )
    ledger_session.add(beat)
    ledger_session.commit()
    assert worker_state(ledger_session, [run])["state"] == "RUNNING"
    beat.checked_at = datetime.now(UTC) - timedelta(seconds=61)
    ledger_session.commit()
    assert worker_state(ledger_session, [run])["state"] == "UNVERIFIED"
    assert worker_state(ledger_session, [])["state"] == "NO_ACTIVE_RUNS"


def test_manual_buy_flows_through_cash_nav_performance_risk_trade_monitor_and_audit(
    client: TestClient, ledger_session: Session
) -> None:
    from decimal import Decimal

    from app.portfolio_operations import TradeMonitorService

    initial = client.get("/api/v1/portfolios/book/summary?end=2026-01-07").json()
    response = client.post(
        "/api/v1/portfolios/book/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": "10",
            "price": "100",
            "commission": "2",
            "notes": "Full operating chain acceptance",
        },
    )
    assert response.status_code == 201, response.text
    after = client.get("/api/v1/portfolios/book/summary?end=2026-01-07").json()
    assert Decimal(initial["portfolio"]["nav"]) == 10000
    assert Decimal(after["portfolio"]["cash"]) == 8998
    assert Decimal(after["portfolio"]["nav"]) == 10198
    assert Decimal(after["portfolio"]["total_pnl"]) == 198
    assert Decimal(after["positions"][0]["quantity"]) == 10
    assert Decimal(after["positions"][0]["market_value"]) == 1200
    assert after["performance"]["twr"] > 0
    assert after["risk"]["gross_exposure"] > 0
    assert after["valuation_run_id"] != initial["valuation_run_id"]
    assert after["accounting"]["reconciliation"]["state"] == "BALANCED"
    trade = TradeMonitorService(ledger_session).list("book")[0]
    assert trade["transaction_id"] == response.json()["id"]
    assert Decimal(trade["weight_before"]) == 0 and Decimal(trade["weight_after"]) > 0
    assert trade["review_state"] == "REQUIRES_REVIEW"
    audit = ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.action == "LEDGER_TRANSACTION_CREATED")
    )
    assert audit.resource_id == response.json()["id"]


def test_logout_all_is_scoped_to_the_authenticated_user(
    ledger_session: Session, session_token: str
) -> None:
    from app.database import get_session
    from app.terminal_api import router
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    other = models.User(email="other@example.invalid", password_hash="test-only", role="VIEWER")
    ledger_session.add(other)
    ledger_session.flush()
    other_session = models.UserSession(
        user_id=other.id,
        session_hash="test-other",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    ledger_session.add(other_session)
    ledger_session.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        response = client.post("/api/v1/auth/logout-all")
        assert response.status_code == 200, response.text
        assert response.json()["revoked"] == 1
        assert ledger_session.get(models.UserSession, other_session.id).revoked_at is None
        assert client.get("/api/v1/auth/session").json()["authenticated"] is False
