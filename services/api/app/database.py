from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

settings = get_settings()
if settings.database_url.startswith("sqlite"):
    engine = create_engine(
        settings.database_url, future=True, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(
        settings.database_url, future=True, pool_pre_ping=True, pool_size=5, max_overflow=10
    )
SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, future=True
)


def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
