"""Wrap-up integration checks for the preserved in-development performance service."""

import pytest
from app.database import get_session
from app.performance_api import router
from app.portfolio_resource_api import router as portfolios
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture
def performance_client(ledger_session, session_token):
    app = FastAPI()
    app.include_router(portfolios)
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        yield client


@pytest.mark.parametrize("view", ["summary", "series", "drawdowns", "monthly", "rolling"])
def test_each_performance_view_uses_the_saved_portfolio(performance_client, view):
    response = performance_client.get(f"/api/v1/performance/portfolios/book/{view}?end=2026-01-09")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["portfolio_id"] == "book"
    assert data["source_precision"] == "DECIMAL"
    assert view in data
    assert data["valuation_run_id"]
    assert "Legacy snapshot" not in " ".join(data["warnings"])


def test_performance_run_is_audited_and_scope_checked(performance_client, ledger_session):
    from app import models

    response = performance_client.post(
        "/api/v1/performance/portfolios/book/calculate", json={"settings": {"end": "2026-01-09"}}
    )
    assert response.status_code == 201, response.text
    data = response.json()
    run_id = data["analysis_run_id"]
    saved = performance_client.get(f"/api/v1/performance/portfolios/book/runs/{run_id}")
    assert saved.json() == data
    audit = ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.resource_id == run_id)
    )
    assert audit.action == "PORTFOLIO_PERFORMANCE_CALCULATED"
    assert (
        performance_client.get(f"/api/v1/performance/portfolios/missing/runs/{run_id}").status_code
        == 404
    )


def test_gross_fees_are_recorded_and_invalid_settings_are_rejected(performance_client):
    url = "/api/v1/performance/portfolios/book/summary"
    response = performance_client.get(url, params={"end": "2026-01-09", "fee_basis": "GROSS"})
    assert response.status_code == 200, response.text
    assert response.json()["summary"]["twr"]["value"] == "0"
    assert response.json()["state"] == "AVAILABLE"
    for params in (
        {"rolling_window": 1},
        {"risk_free_rate": "NaN"},
        {"start": "2026-02-01", "end": "2026-01-01"},
    ):
        assert performance_client.get(url, params=params).status_code == 422
