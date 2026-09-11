"""Archive acknowledgements cannot make local files disappear from the queue."""

import hashlib
import importlib.util
import sqlite3
from collections.abc import Callable, Iterator
from datetime import datetime, tzinfo
from pathlib import Path
from types import ModuleType
from typing import Protocol, Self, runtime_checkable

import httpx
import pytest

DATA = b"date,close\n2026-09-04,210\n"
DIGEST = hashlib.sha256(DATA).hexdigest()


@runtime_checkable
class LocalAgent(Protocol):
    root: Path
    url: str
    db: sqlite3.Connection
    client: httpx.Client
    errors: int

    def scan(self) -> None: ...
    def upload(self) -> None: ...
    def sync(self) -> None: ...
    def close(self) -> None: ...


@pytest.fixture
def agent_module() -> ModuleType:
    source = Path(__file__).resolve().parents[2] / "services/local-agent/agent.py"
    spec = importlib.util.spec_from_file_location("local_agent_recovery", source)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def open_agent(module: ModuleType, root: Path) -> LocalAgent:
    agent = module.Agent(root, "http://127.0.0.1", "isolated-test-token")
    assert isinstance(agent, LocalAgent)
    return agent


@pytest.fixture
def agent(agent_module: ModuleType, tmp_path: Path) -> Iterator[LocalAgent]:
    instance = open_agent(agent_module, tmp_path)
    try:
        yield instance
    finally:
        instance.close()


def transport(agent: LocalAgent, handler: Callable[[httpx.Request], httpx.Response]) -> None:
    agent.client.close()
    agent.client = httpx.Client(base_url=agent.url, transport=httpx.MockTransport(handler))


def queued(agent: LocalAgent) -> Path:
    source = agent.root / "inbox/prices/AAPL.csv"
    source.write_bytes(DATA)
    agent.scan()
    agent.scan()
    row = agent.db.execute("SELECT path FROM files").fetchone()
    assert row is not None and isinstance(row[0], str)
    return Path(row[0])


def response(request: httpx.Request, *, fail_ack: bool = False) -> httpx.Response:
    if request.url.path.endswith("/archived"):
        return httpx.Response(503 if fail_ack else 200, json={"status": "ARCHIVED"})
    item = {"id": "file1", "hash": DIGEST, "state": "MAPPING_REQUIRED"}
    if request.method == "GET":
        return httpx.Response(200, json={"items": [{**item, "state": "IMPORTED"}]})
    return httpx.Response(200, json=item)


class September(datetime):
    @classmethod
    def now(cls, tz: tzinfo | None = None) -> Self:
        return cls(2026, 9, 30, 23, 59, tzinfo=tz)


class October(datetime):
    @classmethod
    def now(cls, tz: tzinfo | None = None) -> Self:
        return cls(2026, 10, 1, tzinfo=tz)


def test_archive_ack_failure_recovers_after_restart_and_month_change(
    agent: LocalAgent,
    agent_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_module, "datetime", September)
    queued(agent)
    transport(agent, lambda request: response(request, fail_ack=True))
    agent.upload()
    agent.sync()
    row = agent.db.execute("SELECT state,archive_path FROM files").fetchone()
    assert row is not None and row[0] == "ARCHIVE_PENDING"
    archived = Path(row[1])
    assert archived.read_bytes() == DATA
    assert archived.parent == agent.root / "processed/2026/09"
    assert agent.errors == 1
    agent.close()
    monkeypatch.setattr(agent_module, "datetime", October)
    restarted = open_agent(agent_module, agent.root)
    transport(restarted, response)
    try:
        restarted.db.execute("UPDATE files SET retry_at=0")
        restarted.db.commit()
        restarted.sync()
        assert restarted.db.execute("SELECT path,state FROM files").fetchone() == (
            str(archived),
            "LOCAL_ARCHIVED",
        )
        assert archived.read_bytes() == DATA
        assert not (restarted.root / "processed/2026/10").exists()
    finally:
        restarted.close()


@pytest.mark.parametrize("damage", ["missing", "changed"])
def test_missing_or_changed_file_is_never_acknowledged_as_archived(
    agent: LocalAgent,
    damage: str,
) -> None:
    queued(agent)
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return response(request)

    transport(agent, handler)
    agent.upload()
    row = agent.db.execute("SELECT path FROM files").fetchone()
    path = Path(row[0])
    if damage == "missing":
        path.unlink()
    else:
        path.write_bytes(b"changed after upload")
    agent.sync()
    assert agent.db.execute("SELECT state FROM files").fetchone()[0] != "LOCAL_ARCHIVED"
    assert not any(url.endswith("/archived") for url in calls)
    assert agent.errors == 1


def test_interrupted_move_retains_its_planned_archive_destination(
    agent: LocalAgent,
    agent_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_module, "datetime", September)
    queued(agent)
    transport(agent, response)
    agent.upload()
    with monkeypatch.context() as interruption:

        def failed_move(path: Path, target: Path) -> Path:
            raise OSError("Isolated rename failure")

        interruption.setattr(Path, "rename", failed_move)
        agent.sync()
    record = agent.db.execute("SELECT path,state,archive_path FROM files").fetchone()
    assert record[1] == "ARCHIVE_PENDING"
    assert Path(record[0]).read_bytes() == DATA
    assert not Path(record[2]).exists()
    monkeypatch.setattr(agent_module, "datetime", October)
    agent.db.execute("UPDATE files SET retry_at=0")
    agent.db.commit()
    agent.sync()
    assert agent.db.execute("SELECT path,state FROM files").fetchone() == (
        record[2],
        "LOCAL_ARCHIVED",
    )
    assert Path(record[2]).read_bytes() == DATA


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"id": "", "hash": DIGEST, "state": "MAPPING_REQUIRED"},
        {"id": "file1", "hash": DIGEST, "state": "UNRECOGNISED"},
        {"id": "file1", "hash": DIGEST, "state": ["IMPORTED"]},
    ],
)
def test_malformed_upload_ack_keeps_original_queued_file(
    agent: LocalAgent, payload: object
) -> None:
    path = queued(agent)
    transport(agent, lambda request: httpx.Response(200, json=payload))
    agent.upload()
    assert agent.db.execute("SELECT state,attempts,file_id FROM files").fetchone() == (
        "QUEUED",
        1,
        None,
    )
    assert path.read_bytes() == DATA


@pytest.mark.parametrize(
    "url",
    [
        "https://",
        "https:///missing",
        "https://example.test:invalid",
        "https://example.test:70000",
        "https://example.test:0",
        "https://@example.test",
        " https://example.test",
        "https://example.test\n",
    ],
)
def test_invalid_server_origins_are_rejected(agent_module: ModuleType, url: str) -> None:
    with pytest.raises(ValueError):
        agent_module.validate_endpoint(url, False)


@pytest.mark.parametrize("status", [None, "OK", "IMPORTED"])
def test_unconfirmed_archive_ack_keeps_the_durable_journal(
    agent: LocalAgent, status: str | None
) -> None:
    queued(agent)

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/archived"):
            return httpx.Response(200, json={"status": status})
        return response(request)

    transport(agent, handler)
    agent.upload()
    agent.sync()
    row = agent.db.execute("SELECT state,archive_path FROM files").fetchone()
    assert row[0] == "ARCHIVE_PENDING"
    assert Path(row[1]).read_bytes() == DATA
    assert agent.errors == 1


def test_legacy_queue_upgrade_retains_the_existing_file(
    agent_module: ModuleType, tmp_path: Path
) -> None:
    logs = tmp_path / "logs"
    logs.mkdir()
    source = tmp_path / "existing.csv"
    source.write_bytes(DATA)
    with sqlite3.connect(logs / "queue.sqlite3") as db:
        db.execute(
            "CREATE TABLE files (path TEXT PRIMARY KEY,hash TEXT NOT NULL,file_id TEXT,state TEXT NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,retry_at REAL NOT NULL DEFAULT 0)"
        )
        db.execute(
            "INSERT INTO files(path,hash,file_id,state,attempts) VALUES(?,?,?,?,?)",
            (str(source), DIGEST, "file1", "IMPORTED", 2),
        )
    instance = open_agent(agent_module, tmp_path)
    try:
        assert instance.db.execute(
            "SELECT path,hash,file_id,state,attempts,archive_path FROM files"
        ).fetchone() == (
            str(source),
            DIGEST,
            "file1",
            "IMPORTED",
            2,
            None,
        )
        assert source.read_bytes() == DATA
        transport(instance, response)
        instance.sync()
        row = instance.db.execute("SELECT path,state FROM files").fetchone()
        assert row[1] == "LOCAL_ARCHIVED"
        assert Path(row[0]).read_bytes() == DATA
    finally:
        instance.close()


def test_existing_archive_name_is_not_overwritten(
    agent: LocalAgent,
    agent_module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(agent_module, "datetime", September)
    original = queued(agent)
    existing = agent.root / "processed/2026/09" / original.name
    existing.parent.mkdir(parents=True)
    existing.write_bytes(b"Older unrelated archive")
    transport(agent, response)
    agent.upload()
    agent.sync()
    row = agent.db.execute("SELECT path,state FROM files").fetchone()
    assert row[1] == "LOCAL_ARCHIVED"
    assert Path(row[0]) != existing
    assert Path(row[0]).read_bytes() == DATA
    assert existing.read_bytes() == b"Older unrelated archive"
