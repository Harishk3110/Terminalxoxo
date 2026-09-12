"""File and agent API contracts retain ownership and explicit failure states."""

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime

import pytest
from app import data_drop_api, models
from app.database import get_session
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def drop_client(ledger_session: Session, session_token: str) -> Iterator[TestClient]:
    application = FastAPI()
    application.include_router(data_drop_api.router)

    def session_override() -> Iterator[Session]:
        yield ledger_session

    application.dependency_overrides[get_session] = session_override
    with TestClient(application) as client:
        client.cookies.set("knk_session", session_token)
        yield client


def test_broker_pairing_requires_an_existing_main_profile(
    drop_client: TestClient, ledger_session: Session
) -> None:
    response = drop_client.post("/api/v1/data-drop/agents/pair", params={"broker": True})
    assert response.status_code == 409
    assert response.json()["detail"] == "Main portfolio profile is not configured"
    assert ledger_session.scalars(select(models.AgentPairing)).all() == []


def test_file_only_pairing_claim_and_heartbeat_do_not_require_a_broker_profile(
    drop_client: TestClient, ledger_session: Session
) -> None:
    response = drop_client.post("/api/v1/data-drop/agents/pair")
    assert response.status_code == 200
    pairing = response.json()
    assert set(pairing) == {"code", "expires_at", "scopes"}
    assert pairing["scopes"] == ["files:upload", "files:status", "agent:heartbeat"]
    assert datetime.fromisoformat(pairing["expires_at"]) > datetime.now(UTC)
    response = drop_client.post("/agent/v1/pair", json={"code": pairing["code"], "name": "Fixture"})
    assert response.status_code == 200
    claimed = response.json()
    assert set(claimed) == {"agent_id", "token", "scopes"}
    assert claimed["scopes"] == pairing["scopes"]
    agent = ledger_session.get(models.LocalAgent, claimed["agent_id"])
    assert agent is not None
    assert agent.token_hash == hashlib.sha256(claimed["token"].encode()).hexdigest()
    assert agent.token_hash != claimed["token"]
    response = drop_client.post("/agent/v1/pair", json={"code": pairing["code"], "name": "Again"})
    assert response.status_code == 403
    response = drop_client.post(
        "/agent/v1/heartbeat",
        headers={"Authorization": "Bearer " + claimed["token"]},
        json={"paused": True, "queued": 0, "errors": 0, "version": "fixture"},
    )
    assert response.status_code == 200
    assert set(response.json()) == {"status", "server_time"}
    assert response.json()["status"] == "OK"
    assert agent.status == {"paused": True, "queued": 0, "errors": 0, "version": "fixture"}


def test_broker_pairing_scope_is_tied_to_the_main_portfolio(
    drop_client: TestClient, ledger_session: Session
) -> None:
    profile = ledger_session.scalar(select(models.PortfolioProfile))
    assert profile is not None
    profile.code = "KNK_MAIN"
    ledger_session.commit()
    response = drop_client.post("/api/v1/data-drop/agents/pair", params={"broker": True})
    assert response.status_code == 200
    assert response.json()["scopes"] == [
        *data_drop_api.SCOPES,
        "broker:read-sync",
        "portfolio:book",
    ]


def test_archiving_unknown_owned_file_is_an_explicit_client_error(
    drop_client: TestClient, ledger_session: Session
) -> None:
    token = "public-disposable-agent-fixture"
    ledger_session.add(
        models.LocalAgent(
            name="Fixture",
            token_hash=hashlib.sha256(token.encode()).hexdigest(),
            scopes=["files:status"],
            status={},
        )
    )
    ledger_session.commit()
    response = drop_client.post(
        "/agent/v1/files/missing/archived", headers={"Authorization": "Bearer " + token}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "File not found"


def test_rejecting_an_unknown_file_is_an_explicit_client_error(drop_client: TestClient) -> None:
    response = drop_client.post(
        "/api/v1/data-drop/files/missing/reject", json={"reason": "Invalid fixture"}
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "File not found"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_mapping_request_rejects_nonfinite_defaults_at_the_http_boundary(value: float) -> None:
    with pytest.raises(ValueError):
        data_drop_api.MappingRequest(profile_id="fixture", defaults={"note": value})


def test_agent_without_an_observed_heartbeat_is_offline_with_no_time(
    drop_client: TestClient, ledger_session: Session
) -> None:
    ledger_session.add(
        models.LocalAgent(name="Offline fixture", token_hash="fixture-only", scopes=[], status={})
    )
    ledger_session.commit()
    response = drop_client.get("/api/v1/data-drop/agents")
    assert response.status_code == 200
    assert response.json()["items"][0]["state"] == "OFFLINE"
    assert response.json()["items"][0]["last_seen"] is None


def test_file_list_and_detail_responses_have_explicit_openapi_contracts(
    drop_client: TestClient,
) -> None:
    schema = drop_client.get("/openapi.json").json()
    for path in ("/api/v1/data-drop/files", "/api/v1/data-drop/files/{file_id}"):
        response = schema["paths"][path]["get"]["responses"]["200"]["content"]["application/json"]
        assert "$ref" in response["schema"]
    payload = schema["components"]["schemas"]["FilePayload"]
    assert len(payload["properties"]) == 16
    assert payload["properties"]["profile_id"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
