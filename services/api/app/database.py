from __future__ import annotations

import sqlite3
from collections.abc import Generator
from contextlib import closing

from pydantic import TypeAdapter
from sqlalchemy import Engine, create_engine, event, make_url
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from .config import get_settings


def create_database_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite":
        return create_engine(url, future=True, pool_pre_ping=True, pool_size=5, max_overflow=10)
    uri = TypeAdapter(bool).validate_python(url.query.get("uri", False))
    memory = url.database in (None, "", ":memory:") or (
        uri and (url.database == "file::memory:" or url.query.get("mode") == "memory")
    )
    version = sqlite3.sqlite_version_info
    if not memory and not (
        version >= (3, 51, 3)
        or (3, 50, 7) <= version < (3, 51, 0)
        or (3, 44, 6) <= version < (3, 45, 0)
    ):
        raise RuntimeError(
            "Local SQLite WAL requires SQLite 3.51.3+ or a fixed 3.50.7/3.44.6 backport; "
            f"this Python runtime uses {'.'.join(map(str, version))}. "
            "Upgrade the Python runtime or use the PostgreSQL Docker stack."
        )
    result = create_engine(url, future=True, connect_args={"check_same_thread": False})
    if not memory:

        def configure_wal(connection: sqlite3.Connection, _record: ConnectionPoolEntry) -> None:
            try:
                # Pool first_connect is synchronized; imports and CLI help stay database-free.
                with closing(connection.cursor()) as cursor:
                    if cursor.execute("PRAGMA journal_mode=WAL").fetchone() != ("wal",):
                        raise RuntimeError("Local SQLite storage does not support WAL journaling")
            except BaseException:
                connection.close()
                raise

        event.listen(result, "first_connect", configure_wal)
    return result


settings = get_settings()
engine = create_database_engine(settings.database_url)
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
