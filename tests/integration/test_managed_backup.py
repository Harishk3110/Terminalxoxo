"""Opt-in real PostgreSQL/MinIO test; creates isolated resources, never overwrites data."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import boto3
import psycopg
import pytest
from dotenv import dotenv_values
from psycopg.rows import TupleRow
from sqlalchemy.engine import make_url

from infrastructure.scripts import managed_postgres
from infrastructure.scripts.managed_backup import create_backup, restore_test
from infrastructure.scripts.managed_backup_contracts import (
    Configuration,
    TableEvidence,
    verify_archive,
)
from infrastructure.scripts.managed_postgres import Postgres

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


def test_postgres_snapshot_and_all_object_classes_restore_privately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = os.environ.get("KNK_MANAGED_BACKUP_TEST_ENV")
    if not env_file:
        pytest.skip("Real PostgreSQL/S3 test requires KNK_MANAGED_BACKUP_TEST_ENV")
    values = dotenv_values(env_file)
    url = make_url(values["DATABASE_URL"] or "").set(
        host=os.environ.get("KNK_TEST_PG_HOST", "127.0.0.1")
    )
    postgres = Postgres(
        url.render_as_string(hide_password=False), os.environ.get("KNK_TEST_PG_TOOLS_CONTAINER")
    )
    identifier = uuid.uuid4().hex
    database = "knk_restore_" + identifier
    bucket = "knk-backup-test-" + identifier
    postgres.create_isolated_database(database)
    source = Postgres(
        url.set(database=database).render_as_string(hide_password=False), postgres.tools_container
    )
    client: S3Client = boto3.client(
        "s3",
        endpoint_url=os.environ.get("KNK_TEST_S3_ENDPOINT", "http://127.0.0.1:9000"),
        aws_access_key_id=values["MINIO_ACCESS_KEY"],
        aws_secret_access_key=values["MINIO_SECRET_KEY"],
        region_name="us-east-1",
    )
    client.create_bucket(Bucket=bucket)
    blobs = {
        "raw/fixture.csv": b"symbol,close\nSAMPLE_EQ,101\n",
        "curated/fixture.json": b'[{"symbol":"SAMPLE_EQ","close":101}]',
        "private-reports/fixture.pdf": b"%PDF fictional report bytes",
        "research-models/fixture.joblib": b"fictional model artifact, never executed",
        "unreferenced/retained.bin": b"Retain all bucket objects, not just current references",
    }
    client.put_object(Bucket=bucket, Key="health/readiness.txt", Body=b"ephemeral probe")
    for key, content in blobs.items():
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType="application/octet-stream",
            Metadata={"fixture": "isolated"},
        )
    with source.connect() as connection:
        for statement in (
            "CREATE TABLE alembic_version (version_num text PRIMARY KEY)",
            "INSERT INTO alembic_version VALUES ('integration-fixture')",
            "CREATE TABLE raw_objects (object_key text, content_hash text, size_bytes bigint)",
            "CREATE TABLE uploaded_files (object_key text, content_hash text, size_bytes bigint)",
            "CREATE TABLE report_jobs (object_key text, content_hash text, size_bytes bigint)",
            "CREATE TABLE dataset_versions (schema_json jsonb)",
            "CREATE TABLE analysis_runs (result jsonb)",
            "CREATE TABLE business_fixture (id integer PRIMARY KEY, amount numeric(24,8), note text)",
            "INSERT INTO business_fixture VALUES (1, 100000.00000001, 'snapshot before concurrent update')",
        ):
            connection.execute(statement)
        for table, key in (
            ("raw_objects", "raw/fixture.csv"),
            ("report_jobs", "private-reports/fixture.pdf"),
        ):
            connection.execute(
                psycopg.sql.SQL("INSERT INTO {} VALUES (%s, %s, %s)").format(
                    psycopg.sql.Identifier(table)
                ),
                (key, hashlib.sha256(blobs[key]).hexdigest(), len(blobs[key])),
            )
        connection.execute(
            "INSERT INTO dataset_versions VALUES (%s)",
            (
                json.dumps(
                    {
                        "curated_key": "curated/fixture.json",
                        "curated_hash": hashlib.sha256(blobs["curated/fixture.json"]).hexdigest(),
                    }
                ),
            ),
        )
        connection.execute(
            "INSERT INTO analysis_runs VALUES (%s)",
            (
                json.dumps(
                    {
                        "artifact": {
                            "object_key": "research-models/fixture.joblib",
                            "content_hash": hashlib.sha256(
                                blobs["research-models/fixture.joblib"]
                            ).hexdigest(),
                            "size_bytes": len(blobs["research-models/fixture.joblib"]),
                        }
                    }
                ),
            ),
        )
    original = managed_postgres.table_snapshot
    snapshot_calls = 0

    def concurrent_change(connection: psycopg.Connection[TupleRow]) -> list[TableEvidence]:
        nonlocal snapshot_calls
        evidence = original(connection)
        snapshot_calls += 1
        if snapshot_calls == 1:
            with source.connect() as writer:
                writer.execute(
                    "UPDATE business_fixture SET amount=200000, note='written after snapshot' WHERE id=1"
                )
        return evidence

    monkeypatch.setattr(managed_postgres, "table_snapshot", concurrent_change)
    result = create_backup(
        source,
        client,
        bucket,
        tmp_path,
        Configuration(
            environment="test", base_currency="SGD", timezone="Asia/Singapore", schema_migrations=[]
        ),
    )
    path = Path(str(result["path"]))
    manifest, evidence = verify_archive(path)
    assert len(manifest.objects) == 5 and len(manifest.references) == 4
    assert "health/readiness.txt" in manifest.excluded_probe_keys
    assert manifest.configuration.schema_migrations == ["integration-fixture"]
    restored = restore_test(source, client, path, evidence.sha256)
    assert restored["state"] == "RESTORED_VERIFIED"
    assert restored["database"] != database and restored["bucket"] != bucket
    with source.connect() as connection:
        row = connection.execute("SELECT amount FROM business_fixture").fetchone()
        assert row is not None and str(row[0]) == "200000.00000000"
    with postgres.connect(str(restored["database"])) as connection:
        row = connection.execute("SELECT amount FROM business_fixture").fetchone()
        assert row is not None and str(row[0]) == "100000.00000001"
    assert snapshot_calls == 2
    (tmp_path / "integration-evidence.json").write_text(
        json.dumps(
            {"source_database": database, "source_bucket": bucket, "restored": restored}, indent=2
        ),
        encoding="utf-8",
    )
