"""MFA enrollment and one-time proof validation; no secrets in audit payloads."""

from __future__ import annotations

import os
import secrets
from datetime import UTC, datetime
from pathlib import Path

import pyotp
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .config import get_settings

hasher = PasswordHasher()


def cipher() -> Fernet:
    key = (os.environ.get("AUTH_SECRET") or get_settings().auth_secret or "").strip()
    if not key:
        if get_settings().knk_env != "local-demo":
            raise HTTPException(503, "Authentication encryption key is not configured")
        path = Path(
            os.environ.get("KNK_AUTH_KEY_FILE")
            or get_settings().auth_key_file
            or str(Path.home() / ".knk-capital" / "auth.key")
        )
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            pass
        else:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(Fernet.generate_key())
        key = path.read_text(encoding="ascii").strip()
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeError) as exc:
        raise HTTPException(503, "Authentication encryption key is invalid") from exc


def encrypt_secret(secret: str) -> str:
    return "fernet:" + cipher().encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_secret(value: str) -> str:
    if value.startswith("local-demo:"):
        if get_settings().knk_env != "local-demo":
            raise HTTPException(503, "Legacy authenticator must be migrated before deployment")
        return value.removeprefix("local-demo:")
    if not value.startswith("fernet:"):
        raise HTTPException(503, "Authenticator secret requires administrator repair")
    try:
        return cipher().decrypt(value.removeprefix("fernet:").encode("ascii")).decode("ascii")
    except (InvalidToken, UnicodeError) as exc:
        raise HTTPException(503, "Authenticator secret cannot be decrypted") from exc


def verify_password(user: models.User, password: str) -> bool:
    try:
        return bool(hasher.verify(user.password_hash, password))
    except (VerificationError, ValueError):
        return False


def totp_state(session: Session, user_id: str) -> models.TotpState:
    state = session.get(models.TotpState, user_id)
    if state is None:
        try:
            with session.begin_nested():
                state = models.TotpState(user_id=user_id, last_timecode=-1)
                session.add(state)
                session.flush()
        except IntegrityError:
            state = session.get(models.TotpState, user_id)
        if state is None:
            raise HTTPException(409, "Authenticator state changed; retry")
    return state


def consume_totp(
    session: Session, user_id: str, secret: str, code: str | None, now: datetime | None = None
) -> bool:
    if not code or len(code) != 6 or not code.isascii() or not code.isdigit():
        return False
    now = now or datetime.now(UTC)
    otp = pyotp.TOTP(secret)
    current = otp.timecode(now)
    step = next(
        (
            step
            for step in (current, current - 1, current + 1)
            if secrets.compare_digest(otp.generate_otp(step), code)
        ),
        None,
    )
    if step is None:
        return False
    totp_state(session, user_id)
    # The conditional UPDATE, not an in-process check, prevents concurrent replay.
    consumed = session.execute(
        update(models.TotpState)
        .where(models.TotpState.user_id == user_id, models.TotpState.last_timecode < step)
        .values(last_timecode=step)
    )
    return consumed.rowcount == 1


def consume_recovery(session: Session, user_id: str, code: str | None) -> bool:
    if not code or len(code) > 128:
        return False
    for row in session.scalars(
        select(models.RecoveryCode).where(
            models.RecoveryCode.user_id == user_id, models.RecoveryCode.used_at.is_(None)
        )
    ):
        try:
            matches = hasher.verify(row.code_hash, code)
        except VerificationError:
            continue
        if matches:
            result = session.execute(
                update(models.RecoveryCode)
                .where(models.RecoveryCode.id == row.id, models.RecoveryCode.used_at.is_(None))
                .values(used_at=datetime.now(UTC))
            )
            return result.rowcount == 1
    return False


def verify_factor(session: Session, user_id: str, code: str | None, recovery: str | None) -> bool:
    setting = session.scalar(
        select(models.TotpSetting).where(models.TotpSetting.user_id == user_id)
    )
    if setting is None or not setting.enabled:
        return not recovery
    if code and recovery:
        return False
    if recovery:
        return consume_recovery(session, user_id, recovery)
    secret = decrypt_secret(setting.secret_encrypted)
    accepted = consume_totp(session, user_id, secret, code)
    if accepted and setting.secret_encrypted.startswith("local-demo:"):
        setting.secret_encrypted = encrypt_secret(secret)
    return accepted


def replace_recovery_codes(session: Session, user_id: str) -> list[str]:
    session.execute(delete(models.RecoveryCode).where(models.RecoveryCode.user_id == user_id))
    codes = [secrets.token_urlsafe(18) for _ in range(8)]
    for code in codes:
        session.add(models.RecoveryCode(user_id=user_id, code_hash=hasher.hash(code)))
    return codes


def revoke_sessions(session: Session, user_id: str, keep_id: str | None = None) -> int:
    result = session.execute(
        update(models.UserSession)
        .where(
            models.UserSession.user_id == user_id,
            models.UserSession.revoked_at.is_(None),
            models.UserSession.id != keep_id,
        )
        .values(revoked_at=datetime.now(UTC))
    )
    return result.rowcount
