import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, TypedDict


class BackupState(TypedDict):
    state: Literal["NOT_VERIFIED", "VERIFIED", "STALE", "FAILED"]
    as_of: str | None
    detail: str


def backup_state(root: Path) -> BackupState:
    receipt = root / "latest-backup.json"
    if not receipt.is_file():
        return {
            "state": "NOT_VERIFIED",
            "as_of": None,
            "detail": "No completed backup verification receipt",
        }
    try:
        if receipt.stat().st_size > 10000:
            raise ValueError("Receipt exceeds limit")
        record = json.loads(receipt.read_text(encoding="utf-8"))
        name = record["archive"]
        if Path(name).name != name or "/" in name or "\\" in name:
            raise ValueError("Invalid archive filename")
        archive = root / name
        stamp = datetime.fromisoformat(record["verified_at"])
        age = (datetime.now(UTC) - stamp).total_seconds()
        if (
            not archive.is_file()
            or archive.stat().st_mtime > stamp.timestamp() + 1
            or age < 0
            or record["state"] != "VERIFIED"
        ):
            raise ValueError("Archive missing, changed or receipt invalid")
        return {
            "state": "VERIFIED" if age < 86400 else "STALE",
            "as_of": stamp.isoformat(),
            "detail": f"Last verification: {record['file_count']} files; SHA-256 {record['sha256'][:16]}; local unencrypted archive. Not a fresh checksum probe.",
        }
    except (OSError, ValueError, KeyError, TypeError):
        return {"state": "FAILED", "as_of": None, "detail": "Backup receipt could not be verified"}
