from datetime import UTC, datetime, timedelta
from typing import Annotated

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from . import models
from .auth_guards import check_login_limit
from .auth_security import (
    consume_totp,
    decrypt_secret,
    encrypt_secret,
    hasher,
    replace_recovery_codes,
    revoke_sessions,
    totp_state,
    verify_factor,
    verify_password,
)
from .auth_sessions import find_session
from .database import get_session
from .portfolio_operations import audit

router = APIRouter(prefix="/api/v1/auth", tags=["Account security"])
SessionDep = Annotated[Session, Depends(get_session)]


class SecurityProof(BaseModel):
    password: str = Field(min_length=1, max_length=1024)
    totp_code: str | None = Field(default=None, max_length=6)
    recovery_code: str | None = Field(default=None, max_length=128)


class PasswordChange(SecurityProof):
    new_password: str = Field(min_length=12, max_length=1024)


def current_user(request: Request, session: Session) -> tuple[models.User, models.UserSession]:
    active = find_session(session, request.cookies.get("knk_session"))
    user = session.get(models.User, active.user_id) if active else None
    if not active or not user or not user.is_active:
        raise HTTPException(401, "Authentication required")
    return user, active


def require_proof(
    session: Session,
    user: models.User,
    payload: SecurityProof,
    request: Request,
    factor: bool = True,
) -> None:
    ip = request.client.host if request.client else None
    check_login_limit(session, user.email, ip)
    if not verify_password(user, payload.password) or (
        factor and not verify_factor(session, user.id, payload.totp_code, payload.recovery_code)
    ):
        session.rollback()
        session.add(
            models.LoginAttempt(
                email=user.email, success=False, failure_reason="security_proof", ip_address=ip
            )
        )
        session.commit()
        raise HTTPException(401, "Invalid password or one-time proof")


@router.get("/security")
def security_status(request: Request, session: SessionDep) -> dict[str, object]:
    user, active = current_user(request, session)
    setting = session.scalar(
        select(models.TotpSetting).where(models.TotpSetting.user_id == user.id)
    )
    sessions = session.scalars(
        select(models.UserSession)
        .where(
            models.UserSession.user_id == user.id,
            models.UserSession.revoked_at.is_(None),
            models.UserSession.expires_at > datetime.now(UTC),
        )
        .order_by(models.UserSession.created_at.desc())
    ).all()
    return {
        "totp_enabled": bool(setting and setting.enabled),
        "recovery_codes_remaining": session.scalar(
            select(func.count())
            .select_from(models.RecoveryCode)
            .where(models.RecoveryCode.user_id == user.id, models.RecoveryCode.used_at.is_(None))
        )
        or 0,
        "sessions": [
            {
                "id": row.id,
                "created_at": row.created_at,
                "expires_at": row.expires_at,
                "current": row.id == active.id,
            }
            for row in sessions
        ],
    }


@router.post("/totp/enroll")
def enroll(payload: SecurityProof, request: Request, session: SessionDep) -> dict[str, object]:
    user, _ = current_user(request, session)
    require_proof(session, user, payload, request, factor=False)
    setting = session.scalar(
        select(models.TotpSetting).where(models.TotpSetting.user_id == user.id)
    )
    if setting and setting.enabled:
        raise HTTPException(409, "Disable the current authenticator before replacing it")
    secret = pyotp.random_base32()
    state = totp_state(session, user.id)
    state.last_timecode = -1
    state.pending_secret = encrypt_secret(secret)
    state.pending_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    audit(session, "AUTH_TOTP_ENROLLMENT_STARTED", "user", user.id, {}, user.id)
    session.commit()
    return {
        "secret": secret,
        "provisioning_uri": pyotp.TOTP(secret).provisioning_uri(
            name=user.email, issuer_name="KnK Capital"
        ),
        "expires_at": state.pending_expires_at,
    }


@router.post("/totp/confirm")
def confirm(payload: SecurityProof, request: Request, session: SessionDep) -> dict[str, object]:
    user, active = current_user(request, session)
    require_proof(session, user, payload, request, factor=False)
    state = totp_state(session, user.id)
    if (
        not state.pending_secret
        or not state.pending_expires_at
        or state.pending_expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)
    ):
        raise HTTPException(409, "Enrollment expired; start again")
    secret = decrypt_secret(state.pending_secret)
    if not consume_totp(session, user.id, secret, payload.totp_code):
        session.add(
            models.LoginAttempt(
                email=user.email,
                success=False,
                failure_reason="enrollment_code",
                ip_address=request.client.host if request.client else None,
            )
        )
        session.commit()
        raise HTTPException(401, "Invalid or already used authenticator code")
    setting = session.scalar(
        select(models.TotpSetting).where(models.TotpSetting.user_id == user.id)
    )
    if setting is None:
        setting = models.TotpSetting(user_id=user.id)
        session.add(setting)
    setting.secret_encrypted, setting.enabled, setting.confirmed_at = (
        state.pending_secret,
        True,
        datetime.now(UTC),
    )
    state.pending_secret, state.pending_expires_at = None, None
    codes = replace_recovery_codes(session, user.id)
    revoke_sessions(session, user.id, keep_id=active.id)
    audit(session, "AUTH_TOTP_ENABLED", "user", user.id, {}, user.id)
    session.commit()
    return {"status": "enabled", "recovery_codes": codes}


@router.post("/totp/disable")
def disable(payload: SecurityProof, request: Request, session: SessionDep) -> dict[str, object]:
    user, active = current_user(request, session)
    require_proof(session, user, payload, request)
    setting = session.scalar(
        select(models.TotpSetting).where(models.TotpSetting.user_id == user.id)
    )
    if setting:
        setting.enabled = False
    state = totp_state(session, user.id)
    state.pending_secret, state.pending_expires_at = None, None
    revoke_sessions(session, user.id, keep_id=active.id)
    audit(session, "AUTH_TOTP_DISABLED", "user", user.id, {}, user.id)
    session.commit()
    return {"status": "disabled"}


@router.post("/recovery-codes")
def regenerate_codes(
    payload: SecurityProof, request: Request, session: SessionDep
) -> dict[str, object]:
    user, _ = current_user(request, session)
    require_proof(session, user, payload, request)
    setting = session.scalar(
        select(models.TotpSetting).where(models.TotpSetting.user_id == user.id)
    )
    if not setting or not setting.enabled:
        raise HTTPException(409, "Enable an authenticator before generating recovery codes")
    codes = replace_recovery_codes(session, user.id)
    audit(session, "AUTH_RECOVERY_CODES_REPLACED", "user", user.id, {}, user.id)
    session.commit()
    return {"recovery_codes": codes}


@router.post("/password")
def change_password(
    payload: PasswordChange,
    request: Request,
    response: Response,
    session: SessionDep,
) -> dict[str, object]:
    user, _ = current_user(request, session)
    require_proof(session, user, payload, request)
    if payload.password == payload.new_password:
        raise HTTPException(422, "Choose a different password")
    user.password_hash = hasher.hash(payload.new_password)
    count = revoke_sessions(session, user.id)
    audit(session, "AUTH_PASSWORD_CHANGED", "user", user.id, {"revoked_sessions": count}, user.id)
    session.commit()
    response.delete_cookie("knk_session")
    return {"status": "signed_out", "revoked_sessions": count}


@router.post("/sessions/{session_id}/revoke")
def revoke_session(
    session_id: str, request: Request, response: Response, session: SessionDep
) -> dict[str, object]:
    user, current = current_user(request, session)
    target = session.get(models.UserSession, session_id)
    if not target or target.user_id != user.id:
        raise HTTPException(404, "Session not found")
    target.revoked_at = datetime.now(UTC)
    audit(session, "AUTH_SESSION_REVOKED", "user_session", session_id, {}, user.id)
    session.commit()
    if current.id == session_id:
        response.delete_cookie("knk_session")
    return {"status": "revoked"}
