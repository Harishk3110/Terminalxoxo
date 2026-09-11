from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field


class BackupReceipt(BaseModel):
    model_config = ConfigDict(strict=True)
    state: Literal["VERIFIED"]
    archive: str
    verified_at: datetime
    file_count: int = Field(ge=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    encryption: Literal["NONE"]
    engine: Literal["sqlite-local", "postgresql-s3"] = "sqlite-local"


class BackupAttempt(BaseModel):
    model_config = ConfigDict(strict=True)
    state: Literal["RUNNING", "FAILED", "VERIFIED"]
    attempted_at: datetime


class BackupState(TypedDict):
    state: Literal["NOT_VERIFIED", "VERIFIED", "STALE", "FAILED"]
    as_of: str | None
    detail: str


def backup_state(root: Path) -> BackupState:
    receipt = root / "latest-backup.json"
    try:
        record = None
        if receipt.is_file():
            if receipt.stat().st_size > 10000:
                raise ValueError("Receipt exceeds limit")
            record = BackupReceipt.model_validate_json(receipt.read_bytes())
        attempt_file = root / "latest-backup-attempt.json"
        if attempt_file.is_file():
            if attempt_file.stat().st_size > 10000:
                raise ValueError("Attempt receipt exceeds limit")
            attempt = BackupAttempt.model_validate_json(attempt_file.read_bytes())
            if attempt.attempted_at.tzinfo is None or attempt.attempted_at > datetime.now(UTC):
                raise ValueError("Invalid attempt timestamp")
            if attempt.state != "VERIFIED" and (
                record is None or attempt.attempted_at > record.verified_at
            ):
                return {
                    "state": "FAILED" if attempt.state == "FAILED" else "NOT_VERIFIED",
                    "as_of": attempt.attempted_at.isoformat(),
                    "detail": "Latest backup failed; previous archives were preserved"
                    if attempt.state == "FAILED"
                    else "Backup attempt has not completed verification",
                }
        if record is None:
            return {
                "state": "NOT_VERIFIED",
                "as_of": None,
                "detail": "No completed backup verification receipt",
            }
        name = record.archive
        if Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("Invalid archive filename")
        archive = root / name
        if not archive.resolve().is_relative_to(root.resolve()):
            raise ValueError("Archive escapes backup directory")
        stamp = record.verified_at
        age = (datetime.now(UTC) - stamp).total_seconds()
        if not archive.is_file() or archive.stat().st_mtime > stamp.timestamp() + 1 or age < 0:
            raise ValueError("Archive missing, changed or receipt invalid")
        return {
            "state": "VERIFIED" if age < 86400 else "STALE",
            "as_of": stamp.isoformat(),
            "detail": f"Last verification: {record.file_count} files; SHA-256 {record.sha256[:16]}; {record.engine} unencrypted archive. Not a fresh checksum probe.",
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {"state": "FAILED", "as_of": None, "detail": "Backup receipt could not be verified"}
