"""Private PostgreSQL/S3 backup, verification and isolated restore. No automatic deletion."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import uuid
from collections.abc import Collection
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import ZIP_DEFLATED, ZipFile

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

from infrastructure.scripts.managed_backup_contracts import (
    HEALTH_PROBE_KEYS,
    MAX_BYTES,
    MAX_MANIFEST,
    MAX_MEMBERS,
    Configuration,
    FileEvidence,
    Manifest,
    ObjectEvidence,
    fingerprint,
    object_member,
    verify_archive,
)
from infrastructure.scripts.managed_postgres import Postgres, dump_snapshot, restore_database

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

type Inventory = dict[str, tuple[int, str, datetime]]


def assert_private_bucket(client: S3Client, bucket: str, sample_key: str | None = None) -> None:
    acl = client.get_bucket_acl(Bucket=bucket)
    if not acl.get("Grants") or any(
        grant.get("Grantee", {}).get("Type") != "CanonicalUser" for grant in acl.get("Grants", [])
    ):
        raise ValueError("Restore bucket has public or unrecognized ACL grants")
    try:
        client.get_bucket_policy(Bucket=bucket)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "NoSuchBucketPolicy":
            raise
    else:
        raise ValueError("New restore bucket unexpectedly has a policy")
    anonymous = boto3.client(
        "s3",
        endpoint_url=client.meta.endpoint_url,
        region_name="us-east-1",
        config=Config(
            signature_version=UNSIGNED,
            connect_timeout=10,
            read_timeout=10,
            retries={"max_attempts": 0},
        ),
    )
    try:
        anonymous.list_objects_v2(Bucket=bucket, MaxKeys=1)
    except ClientError as error:
        if error.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 403:
            raise
    else:
        raise ValueError("Anonymous restore-bucket listing succeeded")
    if sample_key is not None:
        try:
            response = anonymous.get_object(Bucket=bucket, Key=sample_key)
        except ClientError as error:
            if error.response.get("ResponseMetadata", {}).get("HTTPStatusCode") != 403:
                raise
        else:
            response["Body"].close()
            raise ValueError("Anonymous restored-object download succeeded")


def inventory(client: S3Client, bucket: str, excluded_probes: Collection[str] = ()) -> Inventory:
    result: Inventory = {}
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            key, size, etag, modified = (
                item.get("Key"),
                item.get("Size"),
                item.get("ETag"),
                item.get("LastModified"),
            )
            if key is None or size is None or etag is None or modified is None or key in result:
                raise ValueError("Incomplete or duplicate S3 inventory")
            if key in excluded_probes:
                continue
            result[key] = size, etag, modified
            if len(result) + 2 > MAX_MEMBERS:
                raise ValueError("Excessive S3 inventory")
    if sum(row[0] for row in result.values()) > MAX_BYTES:
        raise ValueError("Object store exceeds 20 GB archive limit")
    return result


def write_receipt(destination: Path, record: dict[str, object], name: str) -> None:
    temporary = destination / ("." + uuid.uuid4().hex + ".json")
    with temporary.open("x", encoding="utf-8") as stream:
        os.chmod(temporary, 0o600)
        json.dump(record, stream, sort_keys=True)
    temporary.replace(destination / name)


def create_backup(
    postgres: Postgres,
    client: S3Client,
    bucket: str,
    destination: Path,
    configuration: Configuration,
    *,
    retention_days: int = 30,
) -> dict[str, object]:
    if not 1 <= retention_days <= 3650:
        raise ValueError("Retention must be between 1 and 3650 days")
    destination = destination.resolve()
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    attempt: dict[str, object] = {"state": "RUNNING", "attempted_at": datetime.now(UTC).isoformat()}
    write_receipt(destination, attempt, "latest-backup-attempt.json")
    try:
        result = _create_backup(
            postgres, client, bucket, destination, configuration, retention_days
        )
    except Exception as error:
        write_receipt(
            destination,
            {**attempt, "state": "FAILED", "error_type": type(error).__name__},
            "latest-backup-attempt.json",
        )
        raise
    write_receipt(destination, {**attempt, "state": "VERIFIED"}, "latest-backup-attempt.json")
    return result


def _create_backup(
    postgres: Postgres,
    client: S3Client,
    bucket: str,
    destination: Path,
    configuration: Configuration,
    retention_days: int,
) -> dict[str, object]:
    backup_id = uuid.uuid4().hex
    started = datetime.now(UTC)
    output = destination / f"knk-postgres-{started.strftime('%Y%m%dT%H%M%SZ')}-{backup_id}.zip"
    # An incomplete archive is confined to a private temporary directory and never published.
    with tempfile.TemporaryDirectory(prefix=".knk-backup-", dir=destination) as directory:
        root = Path(directory)
        pending = root / "backup.zip"
        dump = root / "database.dump"
        before = inventory(client, bucket, HEALTH_PROBE_KEYS)
        tables, migrations, references = dump_snapshot(postgres, dump)
        configuration = configuration.model_copy(update={"schema_migrations": migrations})
        objects: list[ObjectEvidence] = []
        files: dict[str, FileEvidence] = {}
        with pending.open("xb") as output_stream:
            os.chmod(pending, 0o600)
            with ZipFile(output_stream, "w", ZIP_DEFLATED) as archive:
                with dump.open("rb") as source:
                    files["database.dump"] = fingerprint(source)
                archive.write(dump, "database.dump")
                total = files["database.dump"].bytes
                for key, (expected_size, etag, modified) in sorted(before.items()):
                    response = client.get_object(Bucket=bucket, Key=key, IfMatch=etag)
                    body = response["Body"]
                    member = object_member(key)
                    digest = hashlib.sha256()
                    size = 0
                    try:
                        with archive.open(member, "w", force_zip64=True) as target:
                            while chunk := body.read(1024 * 1024):
                                size += len(chunk)
                                total += len(chunk)
                                if total > MAX_BYTES or size > expected_size:
                                    raise ValueError(
                                        "Object size or expanded archive limit changed"
                                    )
                                target.write(chunk)
                                digest.update(chunk)
                    finally:
                        body.close()
                    downloaded_at = response.get("LastModified")
                    # HTTP Last-Modified has second precision; listings can retain milliseconds.
                    if (
                        size != expected_size
                        or response.get("ETag") != etag
                        or downloaded_at is None
                        or downloaded_at.replace(microsecond=0) != modified.replace(microsecond=0)
                    ):
                        raise ValueError("Object changed during backup")
                    files[member] = FileEvidence(sha256=digest.hexdigest(), bytes=size)
                    objects.append(
                        ObjectEvidence(
                            key=key,
                            member=member,
                            etag=etag,
                            last_modified=modified,
                            content_type=response.get("ContentType", "application/octet-stream"),
                            metadata=response.get("Metadata", {}),
                        )
                    )
                if inventory(client, bucket, HEALTH_PROBE_KEYS) != before:
                    raise ValueError(
                        "Object inventory changed during backup; pause ingestion and retry"
                    )
                manifest = Manifest(
                    backup_id=backup_id,
                    created_at=started,
                    retain_until=started + timedelta(days=retention_days),
                    files=files,
                    tables=tables,
                    objects=objects,
                    references=references,
                    excluded_probe_keys=list(HEALTH_PROBE_KEYS),
                    configuration=configuration,
                )
                payload = manifest.model_dump_json(indent=2).encode("utf-8")
                if len(payload) > MAX_MANIFEST:
                    raise ValueError("Manifest exceeds size limit")
                archive.writestr("manifest.json", payload)
        verified, archive_hash = verify_archive(pending)
        # Atomic exclusive publication; even a name collision cannot replace an archive.
        os.link(pending, output)
    record: dict[str, object] = {
        "state": "VERIFIED",
        "archive": output.name,
        "created_at": started.isoformat(),
        "verified_at": datetime.now(UTC).isoformat(),
        "sha256": archive_hash.sha256,
        "file_count": len(verified.files),
        "object_count": len(verified.objects),
        "table_count": len(verified.tables),
        "encryption": "NONE",
        "engine": "postgresql-s3",
        "retain_until": verified.retain_until.isoformat(),
        "restore_state": "NOT_TESTED",
    }
    write_receipt(destination, record, "latest-backup.json")
    return {**record, "path": str(output)}


def restore_test(
    postgres: Postgres, client: S3Client, archive_path: Path, expected_hash: str
) -> dict[str, object]:
    identifier = uuid.uuid4().hex
    database = "knk_restore_" + identifier
    bucket = "knk-restore-" + identifier
    with tempfile.TemporaryDirectory(prefix="knk-restore-") as directory:
        root = Path(directory)
        # Use a private verified copy throughout to avoid reopening a replaceable input archive.
        private = root / "backup.zip"
        with archive_path.open("rb") as source, private.open("xb") as target:
            os.chmod(private, 0o600)
            copied = 0
            while chunk := source.read(1024 * 1024):
                copied += len(chunk)
                if copied > MAX_BYTES + MAX_MANIFEST:
                    raise ValueError("Restore input exceeds archive size limit")
                target.write(chunk)
        manifest, evidence = verify_archive(private)
        if evidence.sha256 != expected_hash:
            raise ValueError("Archive hash does not match the trusted backup receipt")
        with ZipFile(private) as archive:
            dump = root / "database.dump"
            with archive.open("database.dump") as source, dump.open("xb") as target:
                os.chmod(dump, 0o600)
                shutil.copyfileobj(source, target)
            # Generated bucket names are never reused, and no existing bucket is emptied.
            if any(item.get("Name") == bucket for item in client.list_buckets().get("Buckets", [])):
                raise ValueError("Isolated restore bucket already exists")
            client.create_bucket(Bucket=bucket)
            assert_private_bucket(client, bucket)
            restore_database(postgres, dump, database, manifest.tables)
            for item in manifest.objects:
                temporary = root / "object.bin"
                with archive.open(item.member) as source, temporary.open("xb") as target:
                    os.chmod(temporary, 0o600)
                    shutil.copyfileobj(source, target)
                with temporary.open("rb") as source:
                    client.put_object(
                        Bucket=bucket,
                        Key=item.key,
                        Body=source,
                        ContentLength=manifest.files[item.member].bytes,
                        ContentType=item.content_type,
                        Metadata=item.metadata,
                        IfNoneMatch="*",
                    )
                temporary.unlink()
                restored = client.get_object(Bucket=bucket, Key=item.key)
                body = restored["Body"]
                try:
                    if fingerprint(body) != manifest.files[item.member]:
                        raise ValueError("Restored object checksum differs")
                finally:
                    body.close()
                if (
                    restored.get("Metadata", {}) != item.metadata
                    or restored.get("ContentType") != item.content_type
                ):
                    raise ValueError("Restored object metadata differs")
            observed = inventory(client, bucket, manifest.excluded_probe_keys)
            if set(observed) != {item.key for item in manifest.objects}:
                raise ValueError("Restored object inventory differs")
            assert_private_bucket(
                client, bucket, manifest.objects[0].key if manifest.objects else None
            )
    record: dict[str, object] = {
        "state": "RESTORED_VERIFIED",
        "verified_at": datetime.now(UTC).isoformat(),
        "archive_hash": evidence.sha256,
        "database": database,
        "bucket": bucket,
        "table_count": len(manifest.tables),
        "object_count": len(manifest.objects),
        "restore_target_is_source": False,
        "cleanup": "MANUAL: isolated resources retained for inspection",
    }
    write_receipt(archive_path.parent, record, "latest-restore.json")
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["backup", "verify", "restore-test"])
    parser.add_argument("--env-file", type=Path)
    parser.add_argument(
        "--database-host", help="Explicit host override for a local forwarded PostgreSQL port"
    )
    parser.add_argument("--s3-endpoint", help="Explicit local/managed S3 endpoint override")
    parser.add_argument(
        "--pg-tools-container", help="Existing PostgreSQL container providing pg_dump/pg_restore"
    )
    parser.add_argument("--destination", type=Path, default=Path("infrastructure/backups"))
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--sha256", help="Expected SHA-256 from the trusted backup receipt")
    parser.add_argument("--retention-days", type=int, default=30)
    parser.add_argument("--acknowledge-unencrypted", action="store_true")
    parser.add_argument("--acknowledge-trusted-source", action="store_true")
    args = parser.parse_args()
    if args.action in {"verify", "restore-test"} and not args.archive:
        parser.error("--archive is required")
    if args.action == "verify":
        manifest, evidence = verify_archive(args.archive)
        print(
            json.dumps(
                {
                    "state": "VERIFIED",
                    "sha256": evidence.sha256,
                    "tables": len(manifest.tables),
                    "objects": len(manifest.objects),
                }
            )
        )
        return 0
    if not args.acknowledge_unencrypted:
        parser.error(
            "--acknowledge-unencrypted is required: archives contain private data and credentials stored in the database"
        )
    if args.action == "restore-test" and (not args.acknowledge_trusted_source or not args.sha256):
        parser.error("Restore executes SQL: --acknowledge-trusted-source and --sha256 are required")
    if args.env_file and not args.env_file.is_file():
        parser.error("Environment file does not exist")
    values = {**(dotenv_values(args.env_file) if args.env_file else {}), **os.environ}
    url = make_url(values.get("DATABASE_URL") or "")
    if args.database_host:
        url = url.set(host=args.database_host)
    postgres = Postgres(url.render_as_string(hide_password=False), args.pg_tools_container)
    postgres.parameters()
    endpoint = args.s3_endpoint or values.get("MINIO_ENDPOINT")
    access, secret = values.get("MINIO_ACCESS_KEY"), values.get("MINIO_SECRET_KEY")
    if not endpoint or not access or not secret:
        parser.error("Explicit S3 endpoint and credentials are required; no local-store fallback")
    client = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access,
        aws_secret_access_key=secret,
        region_name="us-east-1",
        config=Config(connect_timeout=10, read_timeout=120, retries={"max_attempts": 2}),
    )
    if args.action == "backup":
        configuration = Configuration(
            environment=values.get("KNK_ENV") or "UNSPECIFIED",
            base_currency=values.get("KNK_BASE_CURRENCY") or "SGD",
            timezone=values.get("KNK_TIMEZONE") or "Asia/Singapore",
            schema_migrations=[],
        )
        result = create_backup(
            postgres,
            client,
            values.get("OBJECT_STORAGE_BUCKET") or "knk-terminal-local",
            args.destination,
            configuration,
            retention_days=args.retention_days,
        )
    else:
        result = restore_test(postgres, client, args.archive, args.sha256)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        # Connection errors may contain private endpoints or credentials; keep console evidence redacted.
        print(f"Managed backup FAILED ({type(error).__name__}); inspect backup/restore receipts.")
        raise SystemExit(1) from None
