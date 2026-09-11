import asyncio
import hashlib
import importlib.util
import secrets
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from app import models
from app.auth_sessions import token_digest
from app.broker_api import (
    ApproveFillRequest,
    SnapshotRequest,
    account_view,
    approve_fill,
    current_snapshot,
    receive_snapshot,
)
from app.portfolio_operations import PortfolioReconciliationService
from app.portfolio_seed import profile_for
from app.portfolio_valuation import PortfolioValuationService
from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette.requests import Request
from test_portfolio_accounting import accounting_session as accounting_session
from test_portfolio_operations import drop as drop


def test_paper_snapshot_scopes_precedence_missing_fx_and_fill_approval(
    accounting_session: Session,
) -> None:
    session = accounting_session
    main = profile_for(session)
    agent = models.LocalAgent(
        name="Scoped broker",
        token_hash=hashlib.sha256(b"test").hexdigest(),
        scopes=["files:upload"],
        status={},
    )
    session.add(agent)
    session.flush()
    now = datetime.now(UTC)
    payload = SnapshotRequest(
        account="DU123456",
        currency="SGD",
        as_of=now,
        nav="71000",
        cash=[{"currency": "USD", "amount": "100"}],
        positions=[
            {
                "symbol": "AAPL",
                "currency": "USD",
                "quantity": "41",
                "average_cost": "210",
                "market_price": "220",
            }
        ],
        fills=[
            {
                "execution_id": "E1",
                "symbol": "AAPL",
                "currency": "USD",
                "side": "BOT",
                "quantity": "1",
                "price": "220",
                "time": now,
                "commission": "1",
                "commission_currency": "USD",
            }
        ],
    )
    with pytest.raises(HTTPException) as exc:
        receive_snapshot(payload, agent, session)
    assert exc.value.status_code == 403
    agent.scopes = ["broker:read-sync", "portfolio:" + main.portfolio_id]
    result = receive_snapshot(payload, agent, session)
    assert receive_snapshot(payload, agent, session)["duplicate"]
    view = account_view(session, PortfolioValuationService(session).latest())
    assert view["account_source"] == "BROKER" and view["portfolio"]["nav"].startswith("71000")
    assert view["portfolio"]["cash"] is None and view["positions"][0]["market_value"] is None
    assert view["risk"]["beta"] is None and not view["curve"]
    reconcile = PortfolioReconciliationService(session).reconcile()
    assert any(r["type"] == "UNMATCHED_BROKER_FILL" for r in reconcile["items"])
    request = Request({"type": "http", "headers": [], "session": {}})
    approval = ApproveFillRequest(
        snapshot_id=result["id"],
        execution_id="E1",
        transaction_type="BUY",
        fx_rate_to_base="1.29",
        rationale="Verified recorded execution",
    )
    with pytest.raises(HTTPException) as denied:
        approve_fill(approval, request, session)
    assert denied.value.status_code == 403
    token = secrets.token_urlsafe(32)
    user = models.User(
        email="broker-review@example.test", password_hash="test-session-only", role="ADMIN"
    )
    session.add(user)
    session.flush()
    session.add(
        models.UserSession(
            user_id=user.id, session_hash=token_digest(token), expires_at=now + timedelta(hours=1)
        )
    )
    session.commit()
    request = Request({"type": "http", "headers": [(b"cookie", f"knk_session={token}".encode())]})
    added = approve_fill(approval, request, session)
    assert added["trade_event_id"]
    assert approve_fill(approval, request, session)["duplicate"]
    assert not any(
        r["type"] == "UNMATCHED_BROKER_FILL"
        for r in PortfolioReconciliationService(session).reconcile()["items"]
    )
    from app.ledger_contracts import AmendmentRequest, RevisionRequest
    from app.ledger_revisions import PortfolioTransactionService

    corrections = PortfolioTransactionService(session)
    corrections.revise(
        main.portfolio_id,
        added["id"],
        AmendmentRequest(
            expected_version=1,
            reason="Correct the recorded commission",
            changes={"commission": "2"},
        ),
        actor=user.id,
    )
    session.commit()
    assert any(
        r["type"] == "COMMISSION_MISMATCH" and r["internal"] == "2"
        for r in PortfolioReconciliationService(session).reconcile()["items"]
    )
    corrections.revise(
        main.portfolio_id,
        added["id"],
        RevisionRequest(expected_version=2, reason="Void duplicate internal allocation"),
        actor=user.id,
    )
    session.commit()
    assert any(
        r["type"] == "UNMATCHED_BROKER_FILL"
        for r in PortfolioReconciliationService(session).reconcile()["items"]
    )
    agent.revoked_at = now
    session.commit()
    assert not current_snapshot(session, main.portfolio_id)[1]
    assert (
        account_view(session, PortfolioValuationService(session).latest())["account_source"]
        == "INTERNAL LEDGER"
    )


def test_broker_rejects_live_account_and_future_timestamp(accounting_session: Session) -> None:
    session = accounting_session
    agent = models.LocalAgent(
        name="test",
        token_hash="different",
        scopes=["broker:read-sync", "portfolio:" + profile_for(session).portfolio_id],
        status={},
    )
    session.add(agent)
    session.flush()
    with pytest.raises(HTTPException) as exc:
        receive_snapshot(
            SnapshotRequest(account="U12345", currency="SGD", as_of=datetime.now(UTC), nav="1"),
            agent,
            session,
        )
    assert exc.value.status_code == 422


def test_raw_storage_retry_keeps_original_file_id(drop, monkeypatch):
    raw = b"Date,Close\n2026-09-04,215\n"
    original = drop.storage.put_bytes

    def fail(**kwargs):
        raise OSError("Temporary failure")

    monkeypatch.setattr(drop.storage, "put_bytes", fail)
    first = drop.receive("AAPL_2026-09-04.csv", raw)
    assert first["state"] == "UPLOAD_FAILED"
    monkeypatch.setattr(drop.storage, "put_bytes", original)
    retried = drop.receive("AAPL_2026-09-04.csv", raw)
    assert retried["state"] == "MAPPING_REQUIRED" and retried["id"] == first["id"]


def load_agent():
    path = Path(__file__).parents[2] / "local-agent"
    spec = importlib.util.spec_from_file_location("agent", path / "agent.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_agent_queue_retry_archive_and_pause(tmp_path):
    module = load_agent()
    agent = module.Agent(tmp_path, "http://127.0.0.1", "not-a-real-token")
    data = b"date,close\n2026-09-04,210\n"
    source = tmp_path / "inbox" / "prices" / "AAPL.csv"
    source.write_bytes(data)
    calls = []
    failed = [True]

    def transport(request):
        calls.append(request.url.path)
        if request.url.path == "/agent/v1/files" and request.method == "POST":
            return httpx.Response(
                200,
                json={
                    "id": "file1",
                    "hash": hashlib.sha256(data).hexdigest(),
                    "state": "UPLOAD_FAILED" if failed[0] else "MAPPING_REQUIRED",
                },
            )
        if request.url.path == "/agent/v1/files":
            return httpx.Response(200, json={"items": [{"id": "file1", "state": "IMPORTED"}]})
        return httpx.Response(200, json={"status": "OK"})

    agent.client.close()
    agent.client = httpx.Client(base_url=agent.url, transport=httpx.MockTransport(transport))
    try:
        agent.scan()
        assert source.exists()
        agent.scan()
        assert not source.exists()
        agent.upload()
        assert agent.db.execute("SELECT state, attempts FROM files").fetchone() == ("QUEUED", 1)
        failed[0] = False
        agent.db.execute("UPDATE files SET retry_at=0")
        agent.upload()
        assert agent.db.execute("SELECT state FROM files").fetchone()[0] == "MAPPING_REQUIRED"
        agent.sync()
        archived = agent.db.execute("SELECT path,state FROM files").fetchone()
        assert archived[1] == "LOCAL_ARCHIVED" and Path(archived[0]).read_bytes() == data
        (tmp_path / "PAUSE").touch()
        calls.clear()
        agent.tick()
        assert calls == ["/agent/v1/heartbeat"]
    finally:
        agent.close()


def test_broker_reader_is_paper_and_readonly(monkeypatch):
    # Mock the optional broker dependency; the API test environment needs no TWS.
    from enum import IntFlag

    class Fetch(IntFlag):
        POSITIONS = 1
        ACCOUNT_UPDATES = 2
        EXECUTIONS = 4

    observed = {}

    class FakeIB:
        async def connectAsync(self, *args, **kwargs):
            observed.update(kwargs)

        def managedAccounts(self):
            return ["DU12345"]

        async def accountSummaryAsync(self, account):
            return [SimpleNamespace(tag="NetLiquidation", currency="SGD", value="70000")]

        def accountValues(self, account):
            return [SimpleNamespace(tag="CashBalance", currency="SGD", value="70000")]

        def portfolio(self, account):
            return []

        async def reqExecutionsAsync(self, filter):
            return []

        def disconnect(self):
            observed["disconnected"] = True

    monkeypatch.setitem(
        sys.modules,
        "ib_async",
        SimpleNamespace(IB=FakeIB, StartupFetch=Fetch, ExecutionFilter=lambda **kwargs: kwargs),
    )
    monkeypatch.setitem(sys.modules, "agent", load_agent())
    spec = importlib.util.spec_from_file_location(
        "broker_reader", Path(__file__).parents[2] / "local-agent" / "broker_reader.py"
    )
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    args = SimpleNamespace(
        host="127.0.0.1", port=7497, account="DU12345", currency="SGD", client_id=3110
    )
    result = asyncio.run(reader.read_snapshot(args))
    assert result["nav"] == "70000" and observed["readonly"] is True and observed["disconnected"]
    args.port = 7496
    with pytest.raises(ValueError, match="paper"):
        asyncio.run(reader.read_snapshot(args))
