from app import models
from app.database import get_session
from app.terminal_api import router
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select


def test_queue_and_cancel_require_an_actor_and_retain_audit(
    ledger_session, session_token, monkeypatch
):
    monkeypatch.setattr("app.terminal_api.launch_worker", lambda _id: None)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    payload = {"kind": "stress", "name": "Audit test", "parameters": {"portfolio": "book"}}
    with TestClient(app) as client:
        assert client.post("/api/v1/terminal/runs", json=payload).status_code == 403
        client.cookies.set("knk_session", session_token)
        created = client.post("/api/v1/terminal/runs", json=payload)
        assert created.status_code == 202, created.text
        key = created.json()["id"]
        assert created.json()["history"][0]["actor"]
        cancelled = client.post(f"/api/v1/terminal/runs/{key}/cancel")
        assert cancelled.status_code == 200
        actions = ledger_session.scalars(
            select(models.AuditLog.action).where(models.AuditLog.resource_id == key)
        ).all()
        assert "ANALYSIS_RUN_QUEUED" in actions and "ANALYSIS_RUN_CANCELLED" in actions
