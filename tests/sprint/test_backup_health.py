import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.backup_health import backup_state


def receipt(root: Path, stamp: datetime) -> None:
    archive = root / "private-backup.zip"
    archive.write_bytes(b"test receipt only; no archive verification claimed")
    os.utime(archive, (stamp.timestamp() - 1, stamp.timestamp() - 1))
    (root / "latest-backup.json").write_text(
        json.dumps(
            {
                "state": "VERIFIED",
                "archive": archive.name,
                "verified_at": stamp.isoformat(),
                "file_count": 2,
                "sha256": "a" * 64,
                "encryption": "NONE",
                "engine": "postgresql-s3",
            }
        ),
        encoding="utf-8",
    )


def test_postgres_receipt_is_labelled_as_last_verification_only(tmp_path: Path) -> None:
    receipt(tmp_path, datetime.now(UTC) - timedelta(seconds=1))
    state = backup_state(tmp_path)
    assert state["state"] == "VERIFIED"
    assert "postgresql-s3" in state["detail"]
    assert "Not a fresh checksum probe" in state["detail"]


def test_old_receipt_expires(tmp_path: Path) -> None:
    receipt(tmp_path, datetime.now(UTC) - timedelta(days=2))
    assert backup_state(tmp_path)["state"] == "STALE"


def test_failed_attempt_does_not_display_previous_backup_as_healthy(tmp_path: Path) -> None:
    receipt(tmp_path, datetime.now(UTC) - timedelta(hours=1))
    (tmp_path / "latest-backup-attempt.json").write_text(
        json.dumps({"state": "FAILED", "attempted_at": datetime.now(UTC).isoformat()}),
        encoding="utf-8",
    )
    assert backup_state(tmp_path)["state"] == "FAILED"
    assert (tmp_path / "private-backup.zip").is_file()


def test_incomplete_attempt_is_not_verified(tmp_path: Path) -> None:
    (tmp_path / "latest-backup-attempt.json").write_text(
        json.dumps({"state": "RUNNING", "attempted_at": datetime.now(UTC).isoformat()}),
        encoding="utf-8",
    )
    assert backup_state(tmp_path)["state"] == "NOT_VERIFIED"


def test_new_success_is_not_masked_by_an_older_attempt(tmp_path: Path) -> None:
    receipt(tmp_path, datetime.now(UTC) - timedelta(seconds=1))
    (tmp_path / "latest-backup-attempt.json").write_text(
        json.dumps(
            {"state": "FAILED", "attempted_at": (datetime.now(UTC) - timedelta(days=1)).isoformat()}
        ),
        encoding="utf-8",
    )
    assert backup_state(tmp_path)["state"] == "VERIFIED"


def test_malformed_receipt_is_not_healthy(tmp_path: Path) -> None:
    (tmp_path / "latest-backup.json").write_text('{"state":"VERIFIED"}', encoding="utf-8")
    assert backup_state(tmp_path)["state"] == "FAILED"
