"""Local archive contracts reject malformed manifests before creating a restore target."""

import json
import sqlite3
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from infrastructure.scripts.backup_archive import create_backup, restore_backup, verify_backup


@pytest.fixture
def archive(tmp_path: Path) -> Path:
    database = tmp_path / "ledger.sqlite"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE entries (id INTEGER PRIMARY KEY, amount TEXT)")
        connection.execute("INSERT INTO entries VALUES (1, '100000.00000000')")
    objects = tmp_path / "objects"
    objects.mkdir()
    (objects / "source.csv").write_bytes(b"symbol,price\nTEST,100\n")
    return Path(create_backup(database, objects, tmp_path / "backups")["path"])


def replace_manifest(source: Path, target: Path, contents: bytes) -> None:
    with ZipFile(source) as original, ZipFile(target, "w") as output:
        for name in original.namelist():
            output.writestr(name, contents if name == "manifest.json" else original.read(name))


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", True),
        ("created_at", None),
        ("encryption", "ENCRYPTED"),
        ("sensitive", False),
        ("tables", {"entries": True}),
        ("files", None),
    ],
)
def test_invalid_manifest_contract_is_rejected_before_restore(
    archive: Path, tmp_path: Path, field: str, value: object
) -> None:
    with ZipFile(archive) as source:
        manifest: object = json.loads(source.read("manifest.json"))
    assert isinstance(manifest, dict)
    manifest[field] = value
    damaged = tmp_path / "invalid.zip"
    replace_manifest(archive, damaged, json.dumps(manifest).encode())
    target = tmp_path / "restored"
    with pytest.raises(ValueError, match="manifest"):
        restore_backup(damaged, target)
    assert not target.exists()


@pytest.mark.parametrize("contents", [b"null", b"[]", b"{}"])
def test_missing_manifest_structure_has_a_controlled_error(
    archive: Path, tmp_path: Path, contents: bytes
) -> None:
    damaged = tmp_path / "invalid.zip"
    replace_manifest(archive, damaged, contents)
    with pytest.raises(ValueError, match="manifest"):
        verify_backup(damaged)


def test_duplicate_manifest_fields_are_not_silently_overwritten(
    archive: Path, tmp_path: Path
) -> None:
    with ZipFile(archive) as source:
        contents = source.read("manifest.json")
    damaged = tmp_path / "duplicate.zip"
    replace_manifest(archive, damaged, b'{"version":2,' + contents[1:])
    with pytest.raises(ValueError, match="manifest"):
        verify_backup(damaged)


def test_cli_entrypoints_work_from_an_unrelated_directory(archive: Path, tmp_path: Path) -> None:
    scripts = Path(__file__).resolve().parents[2] / "infrastructure/scripts"
    verified = subprocess.run(
        [sys.executable, str(scripts / "verify_backup.py"), str(archive)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert verified.returncode == 0, verified.stderr
    assert json.loads(verified.stdout)["state"] == "VERIFIED"
    target = tmp_path / "cli-restore"
    restored = subprocess.run(
        [sys.executable, str(scripts / "restore.py"), str(archive), "--target", str(target)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert restored.returncode == 0, restored.stderr
    assert json.loads(restored.stdout)["state"] == "RESTORED_VERIFIED"
    assert (target / "objects/source.csv").read_bytes() == b"symbol,price\nTEST,100\n"
    created = subprocess.run(
        [
            sys.executable,
            str(scripts / "backup.py"),
            "--database",
            str(target / "database.sqlite"),
            "--objects",
            str(target / "objects"),
            "--destination",
            str(tmp_path / "cli-backups"),
            "--acknowledge-unencrypted",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert created.returncode == 0, created.stderr
    receipt: object = json.loads(created.stdout)
    assert isinstance(receipt, dict) and receipt["state"] == "VERIFIED"
    checked = verify_backup(Path(receipt["path"]))
    assert checked["manifest"]["tables"] == {"entries": 1}
    assert checked["archive_hash"] == receipt["sha256"]
