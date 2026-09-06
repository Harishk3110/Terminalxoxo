"""Opaque session tokens: only digests are persisted, with legacy session support."""

import hashlib
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models


def token_digest(token: str) -> str:
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()


def find_session(session: Session, token: str | None) -> models.UserSession | None:
    if not token or len(token) > 256:
        return None
    active = select(models.UserSession).where(
        models.UserSession.revoked_at.is_(None),
        models.UserSession.expires_at > datetime.now(UTC),
    )
    row = session.scalar(active.where(models.UserSession.session_hash == token_digest(token)))
    if row:
        return row
    for legacy in session.scalars(active.where(models.UserSession.session_hash.like("$argon2%"))):
        try:
            if PasswordHasher().verify(legacy.session_hash, token):
                return legacy
        except VerificationError:
            continue
    return None
