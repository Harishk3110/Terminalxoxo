"""Local readers must not prevent workspace commits or omit journaled data from backups."""

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest
from app import models
from app.database import create_database_engine
from app.terminal_api import WorkspaceRequest, save_workspace
from sqlalchemy import Connection, Engine, event
from sqlalchemy.orm import Session

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


def test_unsupported_storage_mode_disposes_the_engine(tmp_path: Path) -> None:
    disposed: list[Engine] = []

    def record_disposal(engine: Engine) -> None:
        disposed.append(engine)

    def refuse_wal(
        connection: Connection,
        cursor: object,
        statement: str,
        parameters: object,
        context: object,
        executemany: bool,
    ) -> tuple[str, object]:
        return (
            "PRAGMA journal_mode" if statement == "PRAGMA journal_mode=WAL" else statement,
            parameters,
        )

    event.listen(Engine, "before_cursor_execute", refuse_wal, retval=True)
    event.listen(Engine, "engine_disposed", record_disposal)
    try:
        with pytest.raises(RuntimeError, match="does not support WAL"):
            create_database_engine(f"sqlite:///{(tmp_path / 'unsupported.db').as_posix()}")
        assert len(disposed) == 1
    finally:
        event.remove(Engine, "before_cursor_execute", refuse_wal)
        event.remove(Engine, "engine_disposed", record_disposal)


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
