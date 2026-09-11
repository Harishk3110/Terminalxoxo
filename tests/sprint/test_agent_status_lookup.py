"""Agents can reconcile old queued uploads without listing another agent's files."""

import hashlib
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from app import data_drop_api, models
from app.database import get_session
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from test_local_agent_recovery import (
    DATA,
    DIGEST,
    LocalAgent,
    queued,
    transport,
)
from test_local_agent_recovery import (
    agent as agent,
)
from test_local_agent_recovery import (
    agent_module as agent_module,
)


@pytest.fixture
def status_client() -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    models.Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        session.add_all(
            [
                models.LocalAgent(
                    id=owner,
                    name=owner,
                    token_hash=hashlib.sha256(owner.encode()).hexdigest(),
                    scopes=[] if owner == "denied" else ["files:status"],
                    revoked_at=datetime.now(UTC) if owner == "revoked" else None,
                )
                for owner in ("primary", "other", "denied", "revoked")
            ]
        )
        for index in range(503):
            session.add(
                models.ExternalFile(
                    id=f"file-{index}",
                    filename=f"file-{index}.csv",
                    content_hash=DIGEST,
                    size_bytes=len(DATA),
                    state="IMPORTED",
                    source="TEST",
                    agent_id="other" if index == 502 else "primary",
                    created_at=datetime(2026, 9, 1, tzinfo=UTC) + timedelta(seconds=index),
                )
            )
        session.commit()
    application = FastAPI()
    application.include_router(data_drop_api.router)

    def session_dependency() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    application.dependency_overrides[get_session] = session_dependency
    try:
        with TestClient(application, headers={"Authorization": "Bearer primary"}) as client:
            yield client
    finally:
        engine.dispose()


def test_old_file_lookup_is_scoped_and_not_limited_to_latest_500(
    status_client: TestClient,
) -> None:
    latest = status_client.get("/agent/v1/files")
    assert latest.status_code == 200
    assert len(latest.json()["items"]) == 500
    assert "file-0" not in {item["id"] for item in latest.json()["items"]}
    response = status_client.get(
        "/agent/v1/files", params=[("file_id", "file-0"), ("file_id", "file-502")]
    )
    assert response.status_code == 200
    assert response.json()["items"] == [
        {"id": "file-0", "hash": DIGEST, "state": "IMPORTED", "duplicate_of": None}
    ]


@pytest.mark.parametrize("ids", [[""], ["x" * 201], [str(i) for i in range(101)]])
def test_status_lookup_rejects_unbounded_identifiers(
    status_client: TestClient, ids: list[str]
) -> None:
    response = status_client.get("/agent/v1/files", params=[("file_id", item) for item in ids])
    assert response.status_code == 422


@pytest.mark.parametrize(
    "token,status", [("", 401), ("Bearer denied", 403), ("Bearer revoked", 401)]
)
def test_status_lookup_still_requires_agent_scope(
    status_client: TestClient, token: str, status: int
) -> None:
    response = status_client.get("/agent/v1/files?file_id=file-0", headers={"Authorization": token})
    assert response.status_code == status


def test_agent_reconciles_old_pending_file_in_bounded_identity_batches(agent: LocalAgent) -> None:
    path = queued(agent)
    agent.db.execute("UPDATE files SET file_id='old-file',state='MAPPING_REQUIRED'")
    for index in range(205):
        agent.db.execute(
            "INSERT INTO files(path,hash,file_id,state) VALUES(?,?,?,?)",
            (str(agent.root / "review" / f"{index}.csv"), DIGEST, f"pending-{index}", "MAPPED"),
        )
    agent.db.commit()
    requested: list[list[str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.path.endswith("/old-file/archived")
            return httpx.Response(200, json={"status": "ARCHIVED"})
        identifiers = request.url.params.get_list("file_id")
        requested.append(identifiers)
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": item,
                        "hash": DIGEST,
                        "state": "IMPORTED" if item == "old-file" else "MAPPED",
                    }
                    for item in identifiers
                ]
            },
        )

    transport(agent, handler)
    agent.sync()
    row = agent.db.execute("SELECT path,state FROM files WHERE file_id='old-file'").fetchone()
    assert row[1] == "LOCAL_ARCHIVED"
    assert Path(row[0]).read_bytes() == DATA
    assert not path.exists()
    assert len(requested) == 3
    assert all(1 <= len(batch) <= 100 for batch in requested)
    assert len({item for batch in requested for item in batch}) == 206
    requested.clear()
    agent.sync()
    assert "old-file" not in {item for batch in requested for item in batch}


@pytest.mark.parametrize("returned_id", ["unrequested", ""])
def test_unexpected_status_identity_cannot_change_the_queue(
    agent: LocalAgent, returned_id: str
) -> None:
    path = queued(agent)
    agent.db.execute("UPDATE files SET file_id='old-file',state='MAPPING_REQUIRED'")
    agent.db.commit()
    transport(
        agent,
        lambda request: httpx.Response(
            200,
            json={"items": [{"id": returned_id, "hash": DIGEST, "state": "IMPORTED"}]},
        ),
    )
    with pytest.raises(ValueError):
        agent.sync()
    assert path.read_bytes() == DATA
    assert agent.db.execute("SELECT state FROM files").fetchone()[0] == "MAPPING_REQUIRED"


def test_missing_remote_record_does_not_starve_other_pending_files(agent: LocalAgent) -> None:
    queued(agent)
    agent.db.execute("UPDATE files SET file_id='available',state='MAPPING_REQUIRED'")
    agent.db.execute(
        "INSERT INTO files(path,hash,file_id,state) VALUES(?,?,?,?)",
        (str(agent.root / "review/missing.csv"), DIGEST, "missing", "MAPPED"),
    )
    agent.db.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            assert request.url.path.endswith("/available/archived")
            return httpx.Response(200, json={"status": "ARCHIVED"})
        return httpx.Response(
            200, json={"items": [{"id": "available", "hash": DIGEST, "state": "IMPORTED"}]}
        )

    transport(agent, handler)
    agent.sync()
    archived = agent.db.execute("SELECT path,state FROM files WHERE file_id='available'").fetchone()
    assert archived[1] == "LOCAL_ARCHIVED"
    assert Path(archived[0]).read_bytes() == DATA
    missing = agent.db.execute(
        "SELECT state,attempts,retry_at FROM files WHERE file_id='missing'"
    ).fetchone()
    assert missing[0] == "MAPPED"
    assert missing[1] == 1 and missing[2] > 0
    assert agent.errors == 1


def test_nonterminal_status_cannot_change_the_queued_content_identity(agent: LocalAgent) -> None:
    path = queued(agent)
    agent.db.execute("UPDATE files SET file_id='known',state='MAPPING_REQUIRED'")
    agent.db.commit()
    transport(
        agent,
        lambda request: httpx.Response(
            200, json={"items": [{"id": "known", "hash": "0" * 64, "state": "VALIDATED"}]}
        ),
    )
    agent.sync()
    assert agent.db.execute("SELECT state,hash FROM files").fetchone() == (
        "MAPPING_REQUIRED",
        DIGEST,
    )
    assert path.read_bytes() == DATA
    assert agent.errors == 1
