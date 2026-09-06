from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import func, select

from . import models


def check_login_limit(session, email, ip):
    failures = (
        select(func.count())
        .select_from(models.LoginAttempt)
        .where(
            models.LoginAttempt.success.is_(False),
            models.LoginAttempt.created_at >= datetime.now(UTC) - timedelta(minutes=15),
        )
    )
    account = session.scalar(failures.where(models.LoginAttempt.email == email)) or 0
    network = session.scalar(failures.where(models.LoginAttempt.ip_address == ip)) or 0 if ip else 0
    if account >= 10 or network >= 100:
        raise HTTPException(
            429,
            "Too many sign-in attempts. Try again in 15 minutes.",
            headers={"Retry-After": "900"},
        )


def origin_allowed(method, origin, fetch_site, allowed):
    if method in ("GET", "HEAD", "OPTIONS"):
        return True
    if fetch_site == "cross-site":
        return False
    return origin is None or origin in allowed
