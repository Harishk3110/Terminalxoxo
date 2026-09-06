import pytest
from app import models
from app.alpha_api import router
from app.database import get_session
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture
def alpha_client(ledger_session, session_token):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        yield client


def test_incomplete_alpha_is_saved_with_null_inference_and_valuation(alpha_client, ledger_session):
    response = alpha_client.post(
        "/api/v1/alpha/calculate", json={"portfolio": "book", "performance": {"end": "2026-01-09"}}
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["state"] == "INSUFFICIENT_DATA"
    assert data["inputs"]["valuation_run_id"]
    assert data["results"]["NET"]["p_value"] is None
    run = ledger_session.get(models.AnalysisRun, data["id"])
    assert run.kind == "alpha" and run.result == {
        key: value for key, value in data.items() if key != "id"
    }
    assert ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.action == "ALPHA_ANALYSIS_CREATED")
    )


def test_alpha_rejects_missing_factor_dataset_and_unauthenticated(alpha_client):
    assert (
        alpha_client.post(
            "/api/v1/alpha/calculate", json={"portfolio": "book", "model": "FF3"}
        ).status_code
        == 422
    )
    alpha_client.cookies.clear()
    assert (
        alpha_client.post("/api/v1/alpha/calculate", json={"portfolio": "book"}).status_code == 403
    )
