"""Checksummed SQLite/object archives; never overwrites a restored workspace."""

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import uuid
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import IO, Literal, TypedDict
from zipfile import ZIP_DEFLATED, ZipFile

MAX_EXPANDED = 20_000_000_000


class FileEvidence(TypedDict):
    sha256: str
    bytes: int


class ArchiveManifest(TypedDict):
    version: Literal[1]
    created_at: str
    database: Literal["database.sqlite"]
    encryption: Literal["NONE"]
    sensitive: Literal[True]
    consistency: str
    files: dict[str, FileEvidence]
    tables: dict[str, int]


class BackupReceipt(TypedDict):
    state: Literal["VERIFIED"]
    archive: str
    created_at: str
    verified_at: str
    file_count: int
    sha256: str
    encryption: Literal["NONE"]


class CreatedBackup(BackupReceipt):
    path: str


class VerifiedBackup(TypedDict):
    state: Literal["VERIFIED"]
    manifest: ArchiveManifest
    archive_hash: str


class RestoredBackup(TypedDict):
    state: Literal["RESTORED_VERIFIED"]
    target: str
    archive_hash: str


def unique_manifest_fields(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate backup manifest field")
        result[key] = value
    return result


def archive_manifest(value: object) -> ArchiveManifest:
    if not isinstance(value, dict):
        raise ValueError("Invalid backup manifest")
    if (
        type(value.get("version")) is not int
        or value["version"] != 1
        or value.get("database") != "database.sqlite"
        or value.get("encryption") != "NONE"
        or value.get("sensitive") is not True
    ):
        raise ValueError("Unsupported backup manifest")
    created_at, consistency = value.get("created_at"), value.get("consistency")
    raw_files, raw_tables = value.get("files"), value.get("tables")
    if (
        not isinstance(created_at, str)
        or not isinstance(consistency, str)
        or not consistency
        or not isinstance(raw_files, dict)
        or not isinstance(raw_tables, dict)
    ):
        raise ValueError("Invalid backup manifest fields")
    try:
        timestamp = datetime.fromisoformat(created_at)
    except ValueError:
        raise ValueError("Invalid backup manifest timestamp") from None
    if timestamp.tzinfo is None:
        raise ValueError("Invalid backup manifest timestamp")
    files: dict[str, FileEvidence] = {}
    for name, evidence in raw_files.items():
        if not isinstance(name, str) or not isinstance(evidence, dict):
            raise ValueError("Invalid backup manifest file evidence")
        checksum, size = evidence.get("sha256"), evidence.get("bytes")
        if (
            not isinstance(checksum, str)
            or len(checksum) != 64
            or any(character not in "0123456789abcdef" for character in checksum)
            or type(size) is not int
            or not 0 <= size <= MAX_EXPANDED
        ):
            raise ValueError("Invalid backup manifest file evidence")
        files[name] = {"sha256": checksum, "bytes": size}
    tables: dict[str, int] = {}
    for name, count in raw_tables.items():
        if not isinstance(name, str) or type(count) is not int or count < 0:
            raise ValueError("Invalid backup manifest table count")
        tables[name] = count
    return {
        "version": 1,
        "created_at": created_at,
        "database": "database.sqlite",
        "encryption": "NONE",
        "sensitive": True,
        "consistency": consistency,
        "files": files,
        "tables": tables,
    }


def digest(stream: IO[bytes]) -> str:
    result = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        result.update(chunk)
    return result.hexdigest()


def inspect_database(path: Path) -> dict[str, int]:
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        if db.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise ValueError("SQLite integrity check failed")
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise ValueError("SQLite foreign-key check failed")
        names = [
            row[0]
            for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        return {
            name: db.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0]
            for name in names
        }


def create_backup(database: Path, objects: Path, destination: Path) -> CreatedBackup:
    database, objects, destination = (
        database.resolve(strict=True),
        objects.resolve(strict=True),
        destination.resolve(),
    )
    if not database.is_file() or not objects.is_dir():
        raise ValueError("A SQLite file and local object-store directory are required")
    if destination.is_relative_to(objects):
        raise ValueError("Backup destination must be outside the object store")
    destination.mkdir(parents=True, exist_ok=True)
    backup_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    output = destination / f"knk-backup-{backup_id}.zip"
    manifest: ArchiveManifest = {
        "version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "database": "database.sqlite",
        "encryption": "NONE",
        "sensitive": True,
        "consistency": "SQLite online snapshot; object files hashed individually. Pause ingestion for cross-store consistency.",
        "files": {},
        "tables": {},
    }
    with tempfile.TemporaryDirectory(prefix="knk-backup-") as temporary:
        snapshot = Path(temporary) / "database.sqlite"
        with (
            closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source_db,
            closing(sqlite3.connect(snapshot)) as target_db,
        ):
            source_db.backup(target_db)
        manifest["tables"] = inspect_database(snapshot)
        files = [("database.sqlite", snapshot)]
        for root, dirs, names in os.walk(objects, followlinks=False):
            for directory in dirs:
                entry = Path(root) / directory
                if entry.is_symlink() or (hasattr(entry, "is_junction") and entry.is_junction()):
                    raise ValueError("Object store contains a linked directory")
            for name in names:
                path = Path(root) / name
                if path.is_symlink() or not path.resolve().is_relative_to(objects):
                    raise ValueError("Object store contains a linked file")
                files.append(("objects/" + path.relative_to(objects).as_posix(), path))
        if sum(path.stat().st_size for _, path in files) > MAX_EXPANDED:
            raise ValueError("Local archive limit is 20 GB; use managed backups for larger stores")
        with output.open("xb") as file:
            os.chmod(output, 0o600)
            with ZipFile(file, "w", ZIP_DEFLATED) as archive:
                for name, path in files:
                    before = path.stat()
                    with (
                        path.open("rb") as source,
                        archive.open(name, "w", force_zip64=True) as target,
                    ):
                        checksum = hashlib.sha256()
                        size = 0
                        while chunk := source.read(1024 * 1024):
                            target.write(chunk)
                            checksum.update(chunk)
                            size += len(chunk)
                    after = path.stat()
                    if (
                        before.st_mtime_ns != after.st_mtime_ns
                        or before.st_size != after.st_size
                        or size != before.st_size
                    ):
                        raise ValueError("Object changed during backup; pause ingestion and retry")
                    manifest["files"][name] = {"sha256": checksum.hexdigest(), "bytes": size}
                archive.writestr("manifest.json", json.dumps(manifest, sort_keys=True))
    verified = verify_backup(output)
    receipt: BackupReceipt = {
        "state": "VERIFIED",
        "archive": output.name,
        "created_at": manifest["created_at"],
        "verified_at": datetime.now(UTC).isoformat(),
        "file_count": len(manifest["files"]),
        "sha256": verified["archive_hash"],
        "encryption": "NONE",
    }
    temporary_receipt = destination / f".{backup_id}.json"
    temporary_receipt.write_text(json.dumps(receipt), encoding="utf-8")
    temporary_receipt.replace(destination / "latest-backup.json")
    return {**receipt, "path": str(output)}


def safe_members(archive: ZipFile) -> list[str]:
    members = archive.infolist()
    names = [item.filename for item in members]
    if len(names) != len({name.casefold() for name in names}) or len(names) > 1000000:
        raise ValueError("Duplicate or excessive archive members")
    if sum(item.file_size for item in members) > MAX_EXPANDED:
        raise ValueError("Expanded archive exceeds limit")
    for item in members:
        path = PurePosixPath(item.filename)
        if (
            path.is_absolute()
            or path.as_posix() != item.filename
            or any(
                part in ("..", ".")
                or ":" in part
                or "\\" in part
                or part.endswith((".", " "))
                or PureWindowsPath(part).is_reserved()
                for part in path.parts
            )
            or not path.parts
            or item.is_dir()
        ):
            raise ValueError("Unsafe archive path")
        if item.filename not in (
            "manifest.json",
            "database.sqlite",
        ) and not item.filename.startswith("objects/"):
            raise ValueError("Unexpected archive member")
        if (item.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError("Linked archive member")
    return names


def verify_backup(path: Path) -> VerifiedBackup:
    with ZipFile(path) as archive:
        names = safe_members(archive)
        if "manifest.json" not in names or archive.getinfo("manifest.json").file_size > 25_000_000:
            raise ValueError("Missing or excessive manifest")
        manifest = archive_manifest(
            json.loads(archive.read("manifest.json"), object_pairs_hook=unique_manifest_fields)
        )
        if (
            set(names) != set(manifest["files"]) | {"manifest.json"}
            or "database.sqlite" not in manifest["files"]
        ):
            raise ValueError("Archive and manifest inventory differ")
        for name, evidence in manifest["files"].items():
            with archive.open(name) as source:
                if (
                    archive.getinfo(name).file_size != evidence["bytes"]
                    or digest(source) != evidence["sha256"]
                ):
                    raise ValueError("Backup checksum mismatch")
        with tempfile.TemporaryDirectory(prefix="knk-verify-") as temporary:
            db = Path(temporary) / "database.sqlite"
            with archive.open("database.sqlite") as source, db.open("xb") as target:
                shutil.copyfileobj(source, target)
            if inspect_database(db) != manifest["tables"]:
                raise ValueError("Database row counts do not match manifest")
    with path.open("rb") as stream:
        return {"state": "VERIFIED", "manifest": manifest, "archive_hash": digest(stream)}


def restore_backup(archive_path: Path, target: Path) -> RestoredBackup:
    evidence = verify_backup(archive_path)
    target = target.resolve()
    if target.exists():
        raise ValueError("Restore target must not exist; active data is never overwritten")
    target.mkdir(parents=True, mode=0o700)
    with ZipFile(archive_path) as archive:
        safe_members(archive)
        for name in evidence["manifest"]["files"]:
            path = target / name
            if not path.resolve().is_relative_to(target):
                raise ValueError("Restore path escapes target")
            path.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(name) as source, path.open("xb") as destination:
                os.chmod(path, 0o600)
                shutil.copyfileobj(source, destination)
            with path.open("rb") as restored:
                if digest(restored) != evidence["manifest"]["files"][name]["sha256"]:
                    raise ValueError("Restored file checksum mismatch")
    if inspect_database(target / "database.sqlite") != evidence["manifest"]["tables"]:
        raise ValueError("Restored database verification failed")
    return {
        "state": "RESTORED_VERIFIED",
        "target": str(target),
        "archive_hash": evidence["archive_hash"],
    }
