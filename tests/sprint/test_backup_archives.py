import json
import sqlite3
from pathlib import Path
from zipfile import ZipFile

import pytest
from app.backup_health import backup_state

from infrastructure.scripts.backup_archive import (
    CreatedBackup,
    create_backup,
    inspect_database,
    restore_backup,
    verify_backup,
)


@pytest.fixture
def backup(tmp_path: Path) -> CreatedBackup:
    database = tmp_path / "ledger.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE entries (id INTEGER PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO entries VALUES (1, '100000.00')")
    objects = tmp_path / "objects"
    objects.mkdir()
    (objects / "source.json").write_text('{"data":"original"}', encoding="utf-8")
    return create_backup(database, objects, tmp_path / "backups")


def test_backup_restores_database_objects_and_does_not_overwrite(
    backup: CreatedBackup, tmp_path: Path
) -> None:
    source = Path(backup["path"])
    result = verify_backup(source)
    assert result["manifest"]["tables"] == {"entries": 1}
    assert result["manifest"]["encryption"] == "NONE"
    target = tmp_path / "isolated"
    assert restore_backup(source, target)["state"] == "RESTORED_VERIFIED"
    assert inspect_database(target / "database.sqlite") == {"entries": 1}
    assert json.loads((target / "objects/source.json").read_text())["data"] == "original"
    with pytest.raises(ValueError, match="must not exist"):
        restore_backup(source, target)
    assert backup_state(source.parent)["state"] == "VERIFIED"


def test_tampered_payload_fails_hash_verification(backup: CreatedBackup, tmp_path: Path) -> None:
    corrupted = tmp_path / "corrupted.zip"
    with ZipFile(backup["path"]) as source, ZipFile(corrupted, "w") as target:
        for name in source.namelist():
            target.writestr(
                name, b"tampered" if name == "objects/source.json" else source.read(name)
            )
    with pytest.raises(ValueError, match="checksum"):
        verify_backup(corrupted)


@pytest.mark.parametrize(
    "name",
    [
        "../escape",
        "objects/../../escape",
        "objects/C:/escape",
        "objects/..\\escape",
        "/absolute",
        "objects/NUL",
        "objects/con.txt",
        "objects/COM1/log.txt",
        "objects/LPT9.dat",
    ],
)
def test_path_traversal_fails_before_restore(tmp_path: Path, name: str) -> None:
    archive = tmp_path / "unsafe.zip"
    with ZipFile(archive, "w") as target:
        target.writestr(name, b"unsafe")
    with pytest.raises(ValueError, match="Unsafe"):
        restore_backup(archive, tmp_path / "restored")
    assert not (tmp_path / "restored").exists()


def test_missing_archive_is_not_healthy(backup: CreatedBackup) -> None:
    Path(backup["path"]).rename(Path(backup["path"]).with_suffix(".moved"))
    assert backup_state(Path(backup["path"]).parent)["state"] == "FAILED"
