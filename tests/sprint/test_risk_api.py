from collections.abc import Iterator

import pytest
from app import models
from app.database import get_session
from app.risk_api import router
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def risk_client(ledger_session: Session, session_token: str) -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        yield client


def test_monitor_records_breach_and_configured_threshold_survives_refresh(
    risk_client: TestClient,
) -> None:
    payload = {
        "metric": "gross_exposure",
        "threshold": ".5",
        "direction": "MIN",
        "reason": "Review cash-only test portfolio",
    }
    response = risk_client.post("/api/v1/risk/portfolios/book/limits", json=payload)
    assert response.status_code == 201, response.text
    identifier = response.json()["id"]
    assert response.json() == {
        "id": identifier,
        "metric": "gross_exposure",
        "threshold": "0.5",
        "direction": "MIN",
        "enabled": True,
        "reason": "Review cash-only test portfolio",
    }
    first = risk_client.get("/api/v1/risk/portfolios/book/monitor")
    assert first.status_code == 200, first.text
    limit = first.json()["limits"][0]
    assert limit["state"] == "BREACH"
    assert limit["alert_id"] and first.json()["timeline"]
    second = risk_client.get("/api/v1/risk/portfolios/book/monitor").json()
    assert second["limits"][0]["breach_id"] == limit["breach_id"]
    edited = risk_client.post(
        f"/api/v1/risk/portfolios/book/limits/{identifier}", json={**payload, "enabled": False}
    )
    assert edited.status_code == 200
    assert (
        risk_client.get("/api/v1/risk/portfolios/book/monitor").json()["limits"][0]["state"]
        == "DISABLED"
    )


def test_settings_validate_and_change_valuation_fingerprint(risk_client: TestClient) -> None:
    first = risk_client.get("/api/v1/risk/portfolios/book/monitor").json()
    updated = risk_client.post(
        "/api/v1/risk/portfolios/book/settings",
        json={"simulations": 2000, "reason": "Deterministic sampling review"},
    )
    assert updated.status_code == 200, updated.text
    second = risk_client.get("/api/v1/risk/portfolios/book/monitor").json()
    assert second["valuation_run_id"] != first["valuation_run_id"]
    assert second["model"]["settings"]["simulations"] == 2000
    assert (
        risk_client.post(
            "/api/v1/risk/portfolios/book/settings",
            json={"simulations": 100000000, "reason": "Invalid simulation request"},
        ).status_code
        == 422
    )


def test_risk_configuration_requires_admin_and_unknown_portfolio_is_rejected(
    risk_client: TestClient,
    ledger_session: Session,
) -> None:
    user = ledger_session.scalar(select(models.User))
    assert user is not None
    user.role = "VIEWER"
    ledger_session.commit()
    assert (
        risk_client.post(
            "/api/v1/risk/portfolios/book/settings",
            json={"reason": "Viewer cannot change settings"},
        ).status_code
        == 403
    )
    assert risk_client.get("/api/v1/risk/portfolios/book/monitor").status_code == 200
    assert risk_client.get("/api/v1/risk/portfolios/unknown/monitor").status_code in (404, 422)
    risk_client.cookies.clear()
    assert risk_client.get("/api/v1/risk/portfolios/book/monitor").status_code == 403
