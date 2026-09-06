from copy import deepcopy
from datetime import UTC, datetime

import pytest
from app import models
from app.database import get_session
from app.equity_api import router
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture
def equity_client(ledger_session, session_token, monkeypatch):
    for key in ("AAA", "BBB"):
        ledger_session.add(
            models.FundamentalSnapshot(
                instrument_id=key,
                source="TEST FILE",
                quality="FILE IMPORT",
                as_of=datetime(2025, 12, 31, tzinfo=UTC),
                statements={
                    "items": [
                        {
                            "year": "2025",
                            "revenue": 100,
                            "debt": 20,
                            "cash": 10,
                            "shares": 10,
                            "net_income": 15,
                        }
                    ]
                },
            )
        )
    ledger_session.commit()
    monkeypatch.setattr(
        "app.equity_api.quotes",
        lambda _s: [
            {"id": key, "symbol": key, "price": 10, "quality": "FILE IMPORT", "source": "TEST"}
            for key in ("AAA", "BBB")
        ],
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        yield client


def test_saved_dcf_pins_original_statements_and_audit(equity_client, ledger_session):
    response = equity_client.post(
        "/api/v1/equity/dcf",
        json={
            "symbol": "AAA",
            "scenarios": [{"name": "BASE"}, {"name": "BULL", "revenue_growth": [0.12] * 5}],
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    saved = ledger_session.get(models.AnalysisRun, data["id"])
    original = deepcopy(saved.result)
    ledger_session.scalar(
        select(models.FundamentalSnapshot).where(models.FundamentalSnapshot.instrument_id == "AAA")
    ).statements = {"items": []}
    ledger_session.commit()
    assert saved.result == original and len(data["input_hash"]) == 64
    assert ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.action == "DCF_CREATED")
    )
    assert data["scenarios"][1]["name"] == "BULL"


def test_thesis_versions_preserve_history_and_require_valid_links(equity_client, ledger_session):
    payload = {"symbol": "AAA", "title": "Test thesis", "one_sentence": "A falsifiable thesis"}
    first = equity_client.post("/api/v1/equity/theses", json=payload)
    assert first.status_code == 201, first.text
    second = equity_client.post(
        "/api/v1/equity/theses",
        json={
            **payload,
            "parent_id": first.json()["id"],
            "state": "REVIEW",
            "risks": "Margin contraction",
        },
    )
    assert second.status_code == 201
    assert second.json()["version"] == 2
    assert (
        ledger_session.get(models.InvestmentThesis, first.json()["id"]).summary
        == payload["one_sentence"]
    )
    assert ledger_session.get(models.InvestmentThesis, second.json()["id"]).thesis_state == "REVIEW"
    assert ledger_session.get(models.AnalysisRun, first.json()["id"]).result["state"] == "DRAFT"
    assert len(equity_client.get("/api/v1/equity/theses?symbol=AAA").json()["items"]) == 2
    assert (
        equity_client.post(
            "/api/v1/equity/theses",
            json={**payload, "parent_id": first.json()["id"], "symbol": "BBB"},
        ).status_code
        == 422
    )
    assert (
        equity_client.post(
            "/api/v1/equity/theses", json={**payload, "bull_probability": 0.9}
        ).status_code
        == 422
    )
    assert (
        equity_client.post(
            "/api/v1/equity/theses", json={**payload, "attachment_ids": ["missing"]}
        ).status_code
        == 422
    )


def test_financials_peer_stats_and_auth(equity_client):
    report = equity_client.get("/api/v1/equity/AAA/financials").json()
    assert report["ratios"][0]["pe"] == pytest.approx(100 / 15)
    assert (
        equity_client.get("/api/v1/equity/AAA/financials?frequency=TTM").json()["state"]
        == "INSUFFICIENT_DATA"
    )
    peers = equity_client.post(
        "/api/v1/equity/comparables", json={"symbol": "AAA", "peers": ["AAA", "BBB", "BBB"]}
    )
    assert peers.status_code == 201, peers.text
    assert len(peers.json()["items"]) == 2
    assert peers.json()["statistics"][0]["count"] == 1
    equity_client.cookies.clear()
    assert equity_client.get("/api/v1/equity/AAA/financials").status_code == 403


def test_snapshot_does_not_invent_bid_ask_or_vwap(equity_client):
    response = equity_client.get("/api/v1/equity/AAA/snapshot")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["quote"]["last"] == 120
    assert data["quote"]["bid"] is None and data["quote"]["ask"] is None
    assert data["quote"]["vwap"] is None and data["quote"]["spread"] is None
    assert data["provenance"]["source"] == "TEST"
