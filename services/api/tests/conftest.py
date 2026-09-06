from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))
os.environ.setdefault("DATABASE_URL", "sqlite:///./knk_terminal_test_v3.db")


def pytest_configure(config):
    config.addinivalue_line("markers", "anyio: run async tests with anyio")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def authenticated_token():
    import secrets
    from datetime import UTC, datetime, timedelta
    from app import models
    from app.auth_sessions import token_digest
    from app.database import SessionLocal
    from app.main import ensure_database_ready

    ensure_database_ready()
    token = secrets.token_urlsafe(32)
    with SessionLocal() as session:
        user = models.User(email=f"suite-{secrets.token_hex(8)}@example.test", password_hash="test-session-only", role="ADMIN")
        session.add(user)
        session.flush()
        session.add(models.UserSession(user_id=user.id, session_hash=token_digest(token), expires_at=datetime.now(UTC) + timedelta(hours=1)))
        session.commit()
    return token


@pytest.fixture(autouse=True)
def authenticate_existing_integration_client(request, authenticated_token):
    client = getattr(request.module, "client", None)
    if client is not None:
        client.cookies.set("knk_session", authenticated_token)
