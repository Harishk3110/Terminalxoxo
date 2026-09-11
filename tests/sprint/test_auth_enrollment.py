import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pyotp
import pytest
from app import models
from app.auth_api import router
from app.auth_security import (
    consume_recovery,
    consume_totp,
    decrypt_secret,
    encrypt_secret,
    hasher,
    replace_recovery_codes,
    verify_factor,
)
from app.auth_sessions import token_digest
from app.database import get_session
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select


@pytest.fixture
def account(ledger_session, session_token, monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", Fernet.generate_key().decode())
    user = ledger_session.scalar(
        select(models.User).where(models.User.email == "ledger-tests@example.test")
    )
    password = secrets.token_urlsafe(24)
    user.password_hash = hasher.hash(password)
    ledger_session.commit()
    app = FastAPI()
    app.include_router(router)
    from app.main import login

    app.add_api_route("/api/v1/auth/login", login, methods=["POST"])
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        yield client, user, password, ledger_session


def enrollment(account):
    client, _, password, _ = account
    started = client.post("/api/v1/auth/totp/enroll", json={"password": password})
    assert started.status_code == 200, started.text
    secret = started.json()["secret"]
    code = pyotp.TOTP(secret).now()
    confirmed = client.post(
        "/api/v1/auth/totp/confirm", json={"password": password, "totp_code": code}
    )
    assert confirmed.status_code == 200, confirmed.text
    return secret, code, confirmed.json()["recovery_codes"]


def test_enrollment_encrypts_and_never_exposes_secrets_in_status_or_audit(account):
    client, user, _, session = account
    secret, _, codes = enrollment(account)
    status = client.get("/api/v1/auth/security")
    assert status.json()["totp_enabled"] is True
    assert status.json()["recovery_codes_remaining"] == 8
    setting = session.scalar(
        select(models.TotpSetting).where(models.TotpSetting.user_id == user.id)
    )
    assert setting.secret_encrypted.startswith("fernet:")
    assert secret not in setting.secret_encrypted
    assert decrypt_secret(setting.secret_encrypted) == secret
    payloads = repr(session.scalars(select(models.AuditLog.metadata_json)).all()) + status.text
    assert all(value not in payloads for value in [secret, *codes])


def test_otp_replay_and_recovery_are_rejected_after_first_use(account):
    client, user, password, session = account
    secret, code, codes = enrollment(account)
    client.cookies.clear()
    base = {"email": user.email, "password": password}
    assert client.post("/api/v1/auth/login", json=base).status_code == 401
    assert client.post("/api/v1/auth/login", json={**base, "totp_code": code}).status_code == 401
    assert (
        client.post("/api/v1/auth/login", json={**base, "recovery_code": codes[0]}).status_code
        == 200
    )
    assert (
        client.post("/api/v1/auth/login", json={**base, "recovery_code": codes[0]}).status_code
        == 401
    )
    assert client.get("/api/v1/auth/security").json()["recovery_codes_remaining"] == 7
    assert (
        session.scalar(
            select(models.TotpSetting.enabled).where(models.TotpSetting.user_id == user.id)
        )
        is True
    )


def test_password_change_requires_factor_and_revokes_all_sessions(account):
    client, user, password, session = account
    _, _, codes = enrollment(account)
    new_password = secrets.token_urlsafe(24)
    payload = {"password": password, "new_password": new_password}
    assert client.post("/api/v1/auth/password", json=payload).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/password", json={**payload, "recovery_code": codes[0]}
        ).status_code
        == 200
    )
    assert hasher.verify(user.password_hash, new_password)
    assert client.get("/api/v1/auth/security").status_code == 401
    assert not session.scalars(
        select(models.UserSession).where(
            models.UserSession.user_id == user.id, models.UserSession.revoked_at.is_(None)
        )
    ).all()


def test_expired_enrollment_and_wrong_password_do_not_enable_totp(account):
    client, user, password, session = account
    assert client.post("/api/v1/auth/totp/enroll", json={"password": "wrong"}).status_code == 401
    assert client.post("/api/v1/auth/totp/enroll", json={"password": password}).status_code == 200
    state = session.get(models.TotpState, user.id)
    state.pending_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    session.commit()
    assert (
        client.post(
            "/api/v1/auth/totp/confirm", json={"password": password, "totp_code": "000000"}
        ).status_code
        == 409
    )
    assert client.get("/api/v1/auth/security").json()["totp_enabled"] is False


def test_enrollment_confirmation_counts_failed_attempts(account):
    client, _, password, _ = account
    client.post("/api/v1/auth/totp/enroll", json={"password": password})
    for _ in range(10):
        assert (
            client.post(
                "/api/v1/auth/totp/confirm", json={"password": password, "totp_code": "abc123"}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/v1/auth/totp/confirm", json={"password": password, "totp_code": "abc123"}
        ).status_code
        == 429
    )


def test_enabling_mfa_revokes_other_sessions(account):
    client, user, _, session = account
    other = models.UserSession(
        user_id=user.id,
        session_hash=token_digest(secrets.token_urlsafe(32)),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(other)
    session.commit()
    enrollment(account)
    session.refresh(other)
    assert other.revoked_at is not None
    assert len(client.get("/api/v1/auth/security").json()["sessions"]) == 1


def test_recovery_rotation_invalidates_previous_codes(account):
    client, user, password, session = account
    _, _, codes = enrollment(account)
    rotated = client.post(
        "/api/v1/auth/recovery-codes", json={"password": password, "recovery_code": codes[0]}
    )
    assert rotated.status_code == 200
    assert not consume_recovery(session, user.id, codes[1])
    assert consume_recovery(session, user.id, rotated.json()["recovery_codes"][0])


def test_disable_requires_mfa_and_preserves_password_auth(account):
    client, _, password, _ = account
    _, _, codes = enrollment(account)
    assert client.post("/api/v1/auth/totp/enroll", json={"password": password}).status_code == 409
    assert client.post("/api/v1/auth/totp/disable", json={"password": password}).status_code == 401
    assert (
        client.post(
            "/api/v1/auth/totp/disable", json={"password": password, "recovery_code": codes[0]}
        ).status_code
        == 200
    )
    assert client.get("/api/v1/auth/security").json()["totp_enabled"] is False


def test_session_management_is_scoped_to_user(account):
    client, _, _, session = account
    other = models.User(email="other@example.test", password_hash="not-used")
    session.add(other)
    session.flush()
    foreign = models.UserSession(
        user_id=other.id,
        session_hash="not-a-browser-token",
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    session.add(foreign)
    session.commit()
    assert client.post(f"/api/v1/auth/sessions/{foreign.id}/revoke").status_code == 404
    assert foreign.id not in client.get("/api/v1/auth/security").text
    own = client.get("/api/v1/auth/security").json()["sessions"][0]["id"]
    assert client.post(f"/api/v1/auth/sessions/{own}/revoke").status_code == 200
    assert client.get("/api/v1/auth/security").status_code == 401


@pytest.mark.parametrize(
    "route",
    [
        "security",
        "totp/enroll",
        "totp/confirm",
        "totp/disable",
        "recovery-codes",
        "password",
        "sessions/anything/revoke",
    ],
)
def test_anonymous_security_routes_fail(account, route):
    client, _, password, _ = account
    client.cookies.clear()
    response = (
        client.get("/api/v1/auth/security")
        if route == "security"
        else client.post(
            "/api/v1/auth/" + route,
            json={"password": password, "new_password": secrets.token_urlsafe(24)},
        )
    )
    assert response.status_code == 401


def test_totp_counter_persists_and_does_not_accept_older_steps(account):
    _, user, _, session = account
    secret = pyotp.random_base32()
    now = datetime(2026, 9, 11, 10, tzinfo=UTC)
    otp = pyotp.TOTP(secret)
    assert consume_totp(session, user.id, secret, otp.at(now), now)
    session.commit()
    session.expire_all()
    assert not consume_totp(session, user.id, secret, otp.at(now), now)
    assert not consume_totp(session, user.id, secret, otp.at(now - timedelta(seconds=30)), now)
    later = now + timedelta(seconds=30)
    assert consume_totp(session, user.id, secret, otp.at(later), later)


def test_local_key_is_persistent_and_wrong_key_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("AUTH_SECRET", raising=False)
    path = tmp_path / "private" / "auth.key"
    monkeypatch.setenv("KNK_AUTH_KEY_FILE", str(path))
    value = encrypt_secret("TOTP-TEST-SECRET")
    key = path.read_bytes()
    assert decrypt_secret(value) == "TOTP-TEST-SECRET"
    assert path.read_bytes() == key
    monkeypatch.setenv("AUTH_SECRET", Fernet.generate_key().decode())
    with pytest.raises(HTTPException, match="cannot be decrypted"):
        decrypt_secret(value)


def test_production_rejects_missing_key_and_legacy_plaintext(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "knk_env", "production-paper")
    monkeypatch.delenv("AUTH_SECRET", raising=False)
    with pytest.raises(HTTPException, match="not configured"):
        encrypt_secret("TOTP-TEST-SECRET")
    with pytest.raises(HTTPException, match="migrated"):
        decrypt_secret("local-demo:OLD_SECRET")


def test_recovery_not_accepted_without_mfa_and_both_proofs_rejected(account):
    _, user, _, session = account
    codes = replace_recovery_codes(session, user.id)
    assert not verify_factor(session, user.id, None, codes[0])
    enrollment(account)
    assert not verify_factor(session, user.id, "123456", codes[0])
