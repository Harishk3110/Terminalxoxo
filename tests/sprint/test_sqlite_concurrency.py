"""Local readers must not prevent workspace commits or omit journaled data from backups."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from app import models
from app.database import create_database_engine
from app.terminal_api import WorkspaceRequest, save_workspace
from sqlalchemy import Engine, event
from sqlalchemy.engine import Dialect
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy.pool import ConnectionPoolEntry

from infrastructure.scripts.backup_archive import create_backup, restore_backup


@pytest.fixture
def local_engine(tmp_path: Path) -> Iterator[Engine]:
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'terminal.db').as_posix()}")
    models.Base.metadata.tables[models.Workspace.__tablename__].create(engine)
    models.Base.metadata.tables[models.WorkspaceState.__tablename__].create(engine)
    with Session(engine) as session:
        session.add(models.Workspace(id="main", name="Main"))
        session.add(
            models.WorkspaceState(workspace_id="main", configuration={"route": "/overview"})
        )
        session.commit()
    try:
        yield engine
    finally:
        engine.dispose()


def test_workspace_save_commits_while_another_session_is_reading(local_engine: Engine) -> None:
    with local_engine.connect() as reader, Session(local_engine) as writer:
        # Hold an actual SQLite read transaction, not SQLAlchemy's deferred BEGIN.
        reader.exec_driver_sql("BEGIN")
        assert (
            reader.exec_driver_sql("SELECT name FROM workspaces WHERE id='main'").scalar_one()
            == "Main"
        )
        saved = save_workspace(
            "main", WorkspaceRequest(name="Research", configuration={"route": "/research"}), writer
        )
        assert saved["name"] == "Research"
        assert saved["configuration"] == {"route": "/research"}
        assert (
            reader.exec_driver_sql("SELECT name FROM workspaces WHERE id='main'").scalar_one()
            == "Main"
        )
        reader.rollback()
        assert (
            reader.exec_driver_sql("SELECT name FROM workspaces WHERE id='main'").scalar_one()
            == "Research"
        )


def test_file_sqlite_keeps_durability_and_default_timeout(local_engine: Engine) -> None:
    with local_engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
        assert connection.exec_driver_sql("PRAGMA synchronous").scalar_one() == 2
        assert connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one() == 5000
        assert connection.exec_driver_sql("PRAGMA wal_autocheckpoint").scalar_one() == 1000


def test_engine_creation_does_not_create_a_database_file(tmp_path: Path) -> None:
    target = tmp_path / "lazy.db"
    engine = create_database_engine(f"sqlite:///{target.as_posix()}")
    try:
        assert not target.exists()
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
        assert target.is_file()
    finally:
        engine.dispose()


def test_unavailable_database_path_is_not_opened_until_used(tmp_path: Path) -> None:
    target = tmp_path / "unavailable" / "ledger.db"
    engine = create_database_engine(f"sqlite:///{target.as_posix()}")
    try:
        assert not target.parent.exists()
        with (
            pytest.raises(OperationalError, match="unable to open database file"),
            engine.connect(),
        ):
            pytest.fail("An unavailable database path must not connect")
    finally:
        engine.dispose()


@pytest.mark.parametrize(
    "url",
    [
        "sqlite://",
        "sqlite:///:memory:",
        "sqlite+pysqlite:///:memory:",
        "sqlite:///file::memory:?cache=shared&uri=true",
        "sqlite:///file:knk-memory?mode=memory&cache=shared&uri=true",
    ],
)
def test_memory_sqlite_remains_in_memory(url: str) -> None:
    engine = create_database_engine(url)
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "memory"
            assert connection.exec_driver_sql("PRAGMA database_list").one()[2] == ""
    finally:
        engine.dispose()


@pytest.mark.parametrize("query", ["mode=memory", "mode=memory&uri=false", "mode=memory&uri=False"])
def test_memory_query_without_uri_mode_is_still_a_file(tmp_path: Path, query: str) -> None:
    target = tmp_path / "real-file.db"
    engine = create_database_engine(f"sqlite:///{target.as_posix()}?{query}")
    try:
        with engine.connect() as connection:
            assert target.is_file()
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
    finally:
        engine.dispose()


def test_unsupported_storage_mode_closes_the_failed_connection(tmp_path: Path) -> None:
    connections: list[sqlite3.Connection] = []
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'unsupported.db').as_posix()}")

    def open_memory(
        dialect: Dialect,
        record: ConnectionPoolEntry,
        args: list[object],
        options: dict[str, object],
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(":memory:")
        connections.append(connection)
        return connection

    event.listen(engine, "do_connect", open_memory)
    try:
        with pytest.raises(RuntimeError, match="does not support WAL"), engine.connect():
            pytest.fail("A file-backed configuration must not accept unsupported journaling")
        assert len(connections) == 1
        with pytest.raises(sqlite3.ProgrammingError, match="closed"):
            connections[0].execute("SELECT 1")
    finally:
        event.remove(engine, "do_connect", open_memory)
        engine.dispose()


def test_wal_configuration_runs_once_per_pool_before_connections_are_used(tmp_path: Path) -> None:
    target = tmp_path / "pooled.db"
    engine = create_database_engine(f"sqlite:///{target.as_posix()}")
    statements: list[str] = []

    def traced_connection(
        dialect: Dialect,
        record: ConnectionPoolEntry,
        args: list[object],
        options: dict[str, object],
    ) -> sqlite3.Connection:
        connection = sqlite3.connect(target, check_same_thread=False)
        connection.set_trace_callback(statements.append)
        return connection

    event.listen(engine, "do_connect", traced_connection)
    try:
        with engine.connect() as first, engine.connect() as second:
            assert first.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
            assert second.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
        assert statements.count("PRAGMA journal_mode=WAL") == 1
        engine.dispose()
        with engine.connect() as reopened:
            assert reopened.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
        assert statements.count("PRAGMA journal_mode=WAL") == 2
    finally:
        event.remove(engine, "do_connect", traced_connection)
        engine.dispose()


@pytest.mark.parametrize("version", [(3, 49, 1), (3, 50, 4), (3, 51, 2), (3, 44, 5)])
def test_unsafe_wal_runtime_fails_before_creating_a_database(
    version: tuple[int, int, int], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sqlite3, "sqlite_version_info", version)
    target = tmp_path / "unsafe.db"
    with pytest.raises(RuntimeError, match="Local SQLite WAL requires"):
        create_database_engine(f"sqlite:///{target.as_posix()}")
    assert not target.exists()
    test_memory_sqlite_remains_in_memory("sqlite://")


@pytest.mark.parametrize("version", [(3, 44, 6), (3, 50, 7), (3, 51, 3), (3, 53, 1)])
def test_fixed_wal_versions_are_accepted(
    version: tuple[int, int, int], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sqlite3, "sqlite_version_info", version)
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'supported.db').as_posix()}")
    try:
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
    finally:
        engine.dispose()


def test_postgresql_does_not_connect_or_apply_sqlite_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 49, 1))
    engine = create_database_engine("postgresql+psycopg://localhost/not_connected")
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.pool.status() == (
            "Pool size: 5  Connections in pool: 0 Current Overflow: -5 Current Checked out connections: 0"
        )
    finally:
        engine.dispose()


def test_new_engine_preserves_committed_workspace(local_engine: Engine) -> None:
    other = create_database_engine(local_engine.url.render_as_string(hide_password=False))
    try:
        with other.connect() as connection:
            assert connection.exec_driver_sql("SELECT name FROM workspaces").scalars().all() == [
                "Main"
            ]
            assert connection.exec_driver_sql("PRAGMA journal_mode").scalar_one() == "wal"
    finally:
        other.dispose()


def test_backup_includes_committed_data_not_yet_checkpointed(
    local_engine: Engine, tmp_path: Path
) -> None:
    objects = tmp_path / "objects"
    objects.mkdir()
    with local_engine.connect() as reader, Session(local_engine) as writer:
        reader.exec_driver_sql("BEGIN")
        assert reader.exec_driver_sql("SELECT name FROM workspaces").scalars().all() == ["Main"]
        save_workspace("main", WorkspaceRequest(name="Saved after reader began"), writer)
        journal = tmp_path / "terminal.db-wal"
        assert journal.is_file() and journal.stat().st_size > 0
        receipt = create_backup(tmp_path / "terminal.db", objects, tmp_path / "backups")
        restored = tmp_path / "restored"
        assert restore_backup(Path(receipt["path"]), restored)["state"] == "RESTORED_VERIFIED"
        restored_engine = create_database_engine(
            f"sqlite:///{(restored / 'database.sqlite').as_posix()}"
        )
        try:
            with restored_engine.connect() as connection:
                assert connection.exec_driver_sql(
                    "SELECT name FROM workspaces"
                ).scalars().all() == ["Saved after reader began"]
                assert connection.exec_driver_sql("PRAGMA integrity_check").scalar_one() == "ok"
        finally:
            restored_engine.dispose()
        assert reader.exec_driver_sql("SELECT name FROM workspaces").scalars().all() == ["Main"]
        reader.rollback()
