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
from zipfile import ZIP_DEFLATED, ZipFile

MAX_EXPANDED = 20_000_000_000


def digest(stream):
    result = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        result.update(chunk)
    return result.hexdigest()


def inspect_database(path):
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


def create_backup(database: Path, objects: Path, destination: Path):
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
    manifest = {
        "version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "database": "database.sqlite",
        "encryption": "NONE",
        "sensitive": True,
        "consistency": "SQLite online snapshot; object files hashed individually. Pause ingestion for cross-store consistency.",
        "files": {},
    }
    with tempfile.TemporaryDirectory(prefix="knk-backup-") as temporary:
        snapshot = Path(temporary) / "database.sqlite"
        with (
            closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as source,
            closing(sqlite3.connect(snapshot)) as target,
        ):
            source.backup(target)
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
    receipt = {
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


def safe_members(archive):
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


def verify_backup(path: Path):
    with ZipFile(path) as archive:
        names = safe_members(archive)
        if "manifest.json" not in names or archive.getinfo("manifest.json").file_size > 25_000_000:
            raise ValueError("Missing or excessive manifest")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("version") != 1 or manifest.get("database") != "database.sqlite":
            raise ValueError("Unsupported backup manifest")
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


def restore_backup(archive_path: Path, target: Path):
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
