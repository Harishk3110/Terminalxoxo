"""Provision a private terminal administrator from the server console."""

import getpass
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import models
from app.database import SessionLocal
from argon2 import PasswordHasher
from sqlalchemy import select


def main() -> None:
    email = input("Administrator email: ").strip()
    password = getpass.getpass("Password (at least 12 characters): ")
    if "@" not in email or len(password) < 12:
        raise SystemExit("A valid email and a password of at least 12 characters are required")
    if password != getpass.getpass("Confirm password: "):
        raise SystemExit("Passwords do not match")
    with SessionLocal() as session:
        if session.scalar(select(models.User.id).limit(1)):
            raise SystemExit("An administrator already exists; use the account recovery procedure")
        user = models.User(email=email, password_hash=PasswordHasher().hash(password), role="ADMIN")
        session.add(user)
        session.flush()
        session.add(
            models.AuditLog(
                action="auth.console_setup",
                resource_type="user",
                resource_id=user.id,
                correlation_id=str(uuid.uuid4()),
            )
        )
        session.commit()
    print("Administrator created. No credential was written to a file.")


if __name__ == "__main__":
    main()
