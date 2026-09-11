"""Access checks use real persisted sessions, never a demo-mode authorization bypass."""

import secrets
from datetime import UTC, datetime, timedelta

import pytest
from app import models
from app.auth_sessions import token_digest
from app.database import SessionLocal
from app.main import app, hasher, settings
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.mark.parametrize("environment", ["local-demo", "production-paper"])
@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/terminal/bootstrap",
        "/api/v1/environment",
        "/api/v1/portfolios",
        "/api/v1/operations/portfolio",
        "/api/v1/research",
        "/api/v1/fundamentals/AAPL",
        "/api/v1/desks/quant",
        "/api/v1/providers",
        "/api/v1/terminal/runs",
        "/api/portfolio",
        "/api/risk",
        "/api/environment",
    ],
)
def test_anonymous_investment_requests_are_rejected(monkeypatch, environment, path):
    monkeypatch.setattr(settings, "knk_env", environment)
    with TestClient(app) as anonymous:
        response = anonymous.get(path)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert "noindex" in response.headers["x-robots-tag"]
    assert "KNK_MAIN" not in response.text


def test_no_publishing_route_is_registered():
    paths = [getattr(route, "path", "") for route in app.routes]
    assert not any("/public/" in path or "publish" in path for path in paths)


def test_hosted_admin_setup_is_not_public_registration(monkeypatch):
    monkeypatch.setattr(settings, "knk_env", "production-paper")
    with TestClient(app) as anonymous:
        response = anonymous.post(
            "/api/v1/auth/setup",
            json={
                "email": "blocked@example.test",
                "password": secrets.token_urlsafe(24),
            },
        )
    assert response.status_code == 403


def test_sign_in_logout_revocation_expiry_and_inactive_user():
    email, password = f"login-{secrets.token_hex(6)}@example.test", secrets.token_urlsafe(24)
    with SessionLocal() as session:
        user = models.User(email=email, password_hash=hasher.hash(password), role="ADMIN")
        session.add(user)
        session.commit()
        user_id = user.id
    with TestClient(app) as browser:
        assert browser.get("/api/v1/quotes").status_code == 401
        assert (
            browser.post(
                "/api/v1/auth/login", json={"email": email, "password": "wrong"}
            ).status_code
            == 401
        )
        response = browser.post("/api/v1/auth/login", json={"email": email, "password": password})
        assert response.status_code == 200
        assert "HttpOnly" in response.headers["set-cookie"]
        token = browser.cookies.get("knk_session")
        assert browser.get("/api/v1/quotes").status_code == 200
        with SessionLocal() as session:
            row = session.scalar(
                select(models.UserSession).where(
                    models.UserSession.session_hash == token_digest(token)
                )
            )
            assert row and row.session_hash != token
        assert browser.post("/api/v1/auth/logout").status_code == 200
        browser.cookies.set("knk_session", token)
        assert browser.get("/api/v1/quotes").status_code == 401
        with SessionLocal() as session:
            row = session.scalar(
                select(models.UserSession).where(models.UserSession.user_id == user_id)
            )
            row.revoked_at = None
            row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            session.commit()
        assert browser.get("/api/v1/quotes").status_code == 401
        with SessionLocal() as session:
            row = session.scalar(
                select(models.UserSession).where(models.UserSession.user_id == user_id)
            )
            row.expires_at = datetime.now(UTC) + timedelta(hours=1)
            session.get(models.User, user_id).is_active = False
            session.commit()
        assert browser.get("/api/v1/quotes").status_code == 401
        assert (
            browser.post(
                "/api/v1/auth/login", json={"email": email, "password": password}
            ).status_code
            == 401
        )
