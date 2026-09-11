"""Strict manifest and offline verification for private PostgreSQL/S3 archives."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Literal, Protocol
from zipfile import ZipFile

from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_BYTES = 20_000_000_000
MAX_MEMBERS = 100_000
MAX_MANIFEST = 25_000_000
type ProbeKey = Literal["health/readiness.txt", "health/report-worker.txt", "health/probe.txt"]
HEALTH_PROBE_KEYS: tuple[ProbeKey, ...] = (
    "health/readiness.txt",
    "health/report-worker.txt",
    "health/probe.txt",
)


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class FileEvidence(Contract):
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    bytes: int = Field(ge=0, le=MAX_BYTES)


class TableEvidence(Contract):
    schema_name: str
    table_name: str
    rows: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class ObjectEvidence(Contract):
    key: str = Field(min_length=1, max_length=1024)
    member: str
    etag: str
    last_modified: datetime
    content_type: str
    metadata: dict[str, str]

    @model_validator(mode="after")
    def member_matches_key(self) -> ObjectEvidence:
        if self.member != object_member(self.key):
            raise ValueError("Object member must match its key digest")
        return self


class Configuration(Contract):
    environment: str
    base_currency: str
    timezone: str
    schema_migrations: list[str]
    secrets_included: Literal[False] = False
    cluster_roles_included: Literal[False] = False


class ObjectReference(Contract):
    key: str
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    bytes: int | None = Field(default=None, ge=0)


class Manifest(Contract):
    version: Literal[2] = 2
    engine: Literal["postgresql-s3"] = "postgresql-s3"
    backup_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    created_at: datetime
    retain_until: datetime
    encryption: Literal["NONE"] = "NONE"
    sensitive: Literal[True] = True
    consistency: Literal["EXPORTED_PG_SNAPSHOT_WITH_STABLE_OBJECT_INVENTORY"] = (
        "EXPORTED_PG_SNAPSHOT_WITH_STABLE_OBJECT_INVENTORY"
    )
    files: dict[str, FileEvidence]
    tables: list[TableEvidence]
    objects: list[ObjectEvidence]
    references: list[ObjectReference]
    excluded_probe_keys: list[ProbeKey] = Field(default_factory=list)
    configuration: Configuration

    @model_validator(mode="after")
    def inventory_matches(self) -> Manifest:
        keys = [item.key for item in self.objects]
        members = [item.member for item in self.objects]
        tables = [(item.schema_name, item.table_name) for item in self.tables]
        if len(set(keys)) != len(keys) or len(set(members)) != len(members):
            raise ValueError("Duplicate objects")
        if set(keys) & set(self.excluded_probe_keys):
            raise ValueError("Excluded probes cannot also be archived")
        if not tables or len(set(tables)) != len(tables):
            raise ValueError("Empty or duplicate table inventory")
        if set(self.files) != {"database.dump", *members}:
            raise ValueError("Manifest file/object inventories differ")
        for reference in self.references:
            item = self.files.get(object_member(reference.key))
            if item is None or item.sha256 != reference.sha256:
                raise ValueError("Referenced database object is missing or corrupt")
            if reference.bytes is not None and item.bytes != reference.bytes:
                raise ValueError("Referenced database object size differs")
        if any(stamp.tzinfo is None for stamp in (self.created_at, self.retain_until)):
            raise ValueError("Backup timestamps must include timezone")
        if self.retain_until < self.created_at:
            raise ValueError("Retention precedes backup creation")
        if sum(item.bytes for item in self.files.values()) > MAX_BYTES:
            raise ValueError("Expanded archive exceeds 20 GB")
        return self


def object_member(key: str) -> str:
    # Arbitrary S3 keys are never interpreted as local filesystem paths.
    return "objects/" + hashlib.sha256(key.encode("utf-8")).hexdigest() + ".bin"


class ByteReader(Protocol):
    def read(self, size: int, /) -> bytes: ...


def fingerprint(stream: ByteReader) -> FileEvidence:
    digest = hashlib.sha256()
    size = 0
    while chunk := stream.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_BYTES:
            raise ValueError("Archive stream exceeds 20 GB")
        digest.update(chunk)
    return FileEvidence(sha256=digest.hexdigest(), bytes=size)


def verify_archive(path: Path) -> tuple[Manifest, FileEvidence]:
    with path.open("rb") as stream:
        archive_hash = fingerprint(stream)
        stream.seek(0)
        with ZipFile(stream) as archive:
            members = archive.infolist()
            names = [item.filename for item in members]
            if len(names) > MAX_MEMBERS or len(set(names)) != len(names):
                raise ValueError("Duplicate or excessive archive members")
            if sum(item.file_size for item in members) > MAX_BYTES + MAX_MANIFEST:
                raise ValueError("Expanded archive exceeds limit")
            if "manifest.json" not in names:
                raise ValueError("Missing manifest")
            if archive.getinfo("manifest.json").file_size > MAX_MANIFEST:
                raise ValueError("Excessive manifest")
            manifest = Manifest.model_validate_json(archive.read("manifest.json"))
            if set(names) != {"manifest.json", *manifest.files}:
                raise ValueError("Archive inventory differs from manifest")
            for item in members:
                if item.is_dir() or (item.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("Directory or linked archive member")
            for name, expected in manifest.files.items():
                with archive.open(name) as content:
                    if fingerprint(content) != expected:
                        raise ValueError("Backup checksum mismatch")
            with archive.open("database.dump") as dump:
                if dump.read(5) != b"PGDMP":
                    raise ValueError("Not a PostgreSQL custom-format dump")
    return manifest, archive_hash
