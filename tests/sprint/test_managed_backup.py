from __future__ import annotations

import hashlib
import io
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import Mock
from zipfile import ZipFile

import boto3
import pytest
from botocore.response import StreamingBody
from botocore.stub import Stubber

from infrastructure.scripts import managed_backup as backup
from infrastructure.scripts.managed_backup_contracts import (
    HEALTH_PROBE_KEYS,
    Configuration,
    Manifest,
    ObjectEvidence,
    ObjectReference,
    TableEvidence,
    fingerprint,
    object_member,
    verify_archive,
)
from infrastructure.scripts.managed_postgres import Postgres

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client

NOW = datetime(2026, 9, 12, tzinfo=UTC)
DUMP = b"PGDMP unit-test dump; actual restore is a separate integration gate"
CONTENT = b"fictional immutable raw data"
KEY = "raw/fictitious.csv"
CONFIG = Configuration(
    environment="test", base_currency="SGD", timezone="Asia/Singapore", schema_migrations=["0007"]
)
TABLES = [TableEvidence(schema_name="public", table_name="positions", rows=1, sha256="a" * 64)]


def client() -> S3Client:
    return boto3.client(
        "s3",
        region_name="us-east-1",
        endpoint_url="https://storage.example.invalid",
        aws_access_key_id="fixture",
        aws_secret_access_key="fixture",
    )


def manifest() -> Manifest:
    return Manifest(
        backup_id="a" * 32,
        created_at=NOW,
        retain_until=NOW + timedelta(days=30),
        files={
            "database.dump": fingerprint(io.BytesIO(DUMP)),
            object_member(KEY): fingerprint(io.BytesIO(CONTENT)),
        },
        tables=TABLES,
        objects=[
            ObjectEvidence(
                key=KEY,
                member=object_member(KEY),
                etag='"test"',
                last_modified=NOW,
                content_type="text/csv",
                metadata={"source": "fixture"},
            )
        ],
        references=[
            ObjectReference(key=KEY, sha256=hashlib.sha256(CONTENT).hexdigest(), bytes=len(CONTENT))
        ],
        configuration=CONFIG,
    )


def archive(path: Path, *, content: bytes = CONTENT, extra: str | None = None) -> None:
    with ZipFile(path, "w") as output:
        output.writestr("database.dump", DUMP)
        output.writestr(object_member(KEY), content)
        output.writestr("manifest.json", manifest().model_dump_json())
        if extra:
            output.writestr(extra, b"not allowed")


def test_archive_verifies_checksums_and_private_configuration(tmp_path: Path) -> None:
    path = tmp_path / "backup.zip"
    archive(path)
    result, evidence = verify_archive(path)
    assert result == manifest()
    assert evidence.sha256 == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result.encryption == "NONE" and result.sensitive
    assert result.configuration.secrets_included is False
    assert result.configuration.cluster_roles_included is False


def test_tampering_fails_even_when_size_matches(tmp_path: Path) -> None:
    path = tmp_path / "backup.zip"
    archive(path, content=b"x" * len(CONTENT))
    with pytest.raises(ValueError, match="checksum"):
        verify_archive(path)


@pytest.mark.parametrize("extra", ["../escape", "/absolute", "objects/fake.bin", "database.sqlite"])
def test_unmanifested_paths_are_rejected(tmp_path: Path, extra: str) -> None:
    path = tmp_path / "backup.zip"
    archive(path, extra=extra)
    with pytest.raises(ValueError, match="inventory"):
        verify_archive(path)


def test_duplicate_members_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "backup.zip"
    archive(path)
    with ZipFile(path, "a") as output, pytest.warns(UserWarning, match="Duplicate"):
        output.writestr("database.dump", DUMP)
    with pytest.raises(ValueError, match="Duplicate"):
        verify_archive(path)


def test_object_keys_are_encoded_not_extracted_as_paths() -> None:
    for key in ("../../secret", "C:\\windows\\file", "a/../b", "raw/report.pdf"):
        member = object_member(key)
        assert len(Path(member).parts) == 2
        assert member.startswith("objects/") and member.endswith(".bin")
        assert ".." not in member and "\\" not in member


@pytest.mark.parametrize(
    "mutation", ["missing", "hash", "size", "duplicate", "empty_tables", "unexpected"]
)
def test_manifest_rejects_inconsistent_evidence(mutation: str) -> None:
    data = json.loads(manifest().model_dump_json())
    if mutation == "missing":
        data["references"][0]["key"] = "absent"
    elif mutation == "hash":
        data["references"][0]["sha256"] = "b" * 64
    elif mutation == "size":
        data["references"][0]["bytes"] += 1
    elif mutation == "duplicate":
        data["objects"].append(data["objects"][0])
    elif mutation == "empty_tables":
        data["tables"] = []
    else:
        data["configuration"]["AUTH_SECRET"] = "must not be exported"
    with pytest.raises(ValueError):
        Manifest.model_validate_json(json.dumps(data))


@pytest.mark.parametrize(
    "url", ["sqlite:///data.db", "postgresql://host/", "postgresql://host/db?options=unsafe"]
)
def test_postgres_requires_explicit_supported_database(url: str) -> None:
    with pytest.raises(ValueError):
        Postgres(url).parameters()


@pytest.mark.parametrize(
    "name", ["knk_terminal", "postgres", "knk_restore_existing", '"; DROP DATABASE x']
)
def test_restore_refuses_nonisolated_names_before_connecting(
    name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    connection = Mock(side_effect=AssertionError("Must not connect"))
    monkeypatch.setattr(Postgres, "connect", connection)
    with pytest.raises(ValueError, match="isolated"):
        Postgres("postgresql://knk@localhost/knk_terminal").create_isolated_database(name)
    connection.assert_not_called()


def test_pg_commands_never_include_password_or_destructive_flags(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = Mock(return_value=subprocess.CompletedProcess([], 0, stderr=b""))
    monkeypatch.setattr(subprocess, "run", runner)
    postgres = Postgres(
        "postgresql://knk:private-fixture@localhost/knk_terminal", "existing-postgres"
    )
    postgres.run("pg_dump", ["--format=custom", "--snapshot=test"])
    arguments = runner.call_args.args[0]
    assert "private-fixture" not in repr(arguments)
    assert "PGPASSWORD" in arguments
    assert runner.call_args.kwargs["env"]["PGPASSWORD"] == "private-fixture"
    assert "--clean" not in arguments and "--create" not in arguments
    assert "private-fixture" not in repr(postgres)


def test_pg_tool_failure_is_not_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        Mock(return_value=subprocess.CompletedProcess([], 2, stderr=b"private connection error")),
    )
    with pytest.raises(RuntimeError, match="exit code 2") as failure:
        Postgres("postgresql://knk@localhost/db").run("pg_dump", [])
    assert "private connection" not in str(failure.value)


def test_pg_warnings_are_not_silently_certified(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        subprocess, "run", Mock(return_value=subprocess.CompletedProcess([], 0, stderr=b"warning"))
    )
    with pytest.raises(RuntimeError, match="diagnostics"):
        Postgres("postgresql://knk@localhost/db").run("pg_dump", [])


def snapshot_fixture(
    postgres: Postgres, path: Path
) -> tuple[list[TableEvidence], list[str], list[ObjectReference]]:
    path.write_bytes(DUMP)
    return TABLES, ["0007"], manifest().references


@pytest.mark.parametrize("changed", [False, True])
def test_backup_detects_inventory_changes_and_only_publishes_verified_archives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: bool
) -> None:
    s3 = client()
    listing = {
        "Contents": [{"Key": KEY, "Size": len(CONTENT), "ETag": '"test"', "LastModified": NOW}]
    }
    monkeypatch.setattr(backup, "dump_snapshot", snapshot_fixture)
    with Stubber(s3) as stub:
        stub.add_response("list_objects_v2", listing, {"Bucket": "source"})
        stub.add_response(
            "get_object",
            {
                "Body": StreamingBody(io.BytesIO(CONTENT), len(CONTENT)),
                "ETag": '"test"',
                "LastModified": NOW.replace(microsecond=902000),
                "ContentType": "text/csv",
            },
            {"Bucket": "source", "Key": KEY, "IfMatch": '"test"'},
        )
        stub.add_response(
            "list_objects_v2", {"Contents": []} if changed else listing, {"Bucket": "source"}
        )
        if changed:
            with pytest.raises(ValueError, match="inventory changed"):
                backup.create_backup(
                    Postgres("postgresql://host/db"), s3, "source", tmp_path, CONFIG
                )
            assert list(tmp_path.glob("*.zip")) == []
            assert not (tmp_path / "latest-backup.json").exists()
            assert (
                json.loads((tmp_path / "latest-backup-attempt.json").read_text())["state"]
                == "FAILED"
            )
        else:
            result = backup.create_backup(
                Postgres("postgresql://host/db"), s3, "source", tmp_path, CONFIG
            )
            assert result["state"] == "VERIFIED" and result["restore_state"] == "NOT_TESTED"
            assert (tmp_path / "latest-backup.json").is_file()
            outputs = list(tmp_path.glob("*.zip"))
            assert len(outputs) == 1
            assert verify_archive(outputs[0])[0].references == manifest().references
        stub.assert_no_pending_responses()


def test_restore_refuses_wrong_trusted_hash_before_creating_resources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "backup.zip"
    archive(path)
    restore = Mock(side_effect=AssertionError("No resource creation"))
    monkeypatch.setattr(backup, "restore_database", restore)
    s3 = client()
    with Stubber(s3):
        with pytest.raises(ValueError, match="trusted backup receipt"):
            backup.restore_test(Postgres("postgresql://host/db"), s3, path, "f" * 64)
    restore.assert_not_called()
    assert not (tmp_path / "latest-restore.json").exists()


def test_negative_retention_fails_before_any_io(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Retention"):
        backup.create_backup(
            Postgres("postgresql://host/db"),
            client(),
            "source",
            tmp_path / "not-created",
            CONFIG,
            retention_days=0,
        )
    assert not (tmp_path / "not-created").exists()


def test_public_acl_is_rejected_before_anonymous_probe() -> None:
    s3 = client()
    with Stubber(s3) as stub:
        stub.add_response(
            "get_bucket_acl",
            {
                "Grants": [
                    {
                        "Grantee": {
                            "Type": "Group",
                            "URI": "http://acs.amazonaws.com/groups/global/AllUsers",
                        },
                        "Permission": "READ",
                    }
                ]
            },
            {"Bucket": "fixture"},
        )
        with pytest.raises(ValueError, match="public"):
            backup.assert_private_bucket(s3, "fixture")
        stub.assert_no_pending_responses()


def test_unexpected_bucket_policy_is_not_ignored() -> None:
    s3 = client()
    with Stubber(s3) as stub:
        stub.add_response(
            "get_bucket_acl",
            {
                "Grants": [
                    {
                        "Grantee": {"Type": "CanonicalUser", "ID": "owner"},
                        "Permission": "FULL_CONTROL",
                    }
                ]
            },
            {"Bucket": "fixture"},
        )
        stub.add_response("get_bucket_policy", {"Policy": "{}"}, {"Bucket": "fixture"})
        with pytest.raises(ValueError, match="policy"):
            backup.assert_private_bucket(s3, "fixture")
        stub.assert_no_pending_responses()


def test_only_named_health_probe_objects_are_excluded() -> None:
    s3 = client()
    keys = [*HEALTH_PROBE_KEYS, "raw/fixture.csv", "health/user-data.csv"]
    with Stubber(s3) as stub:
        stub.add_response(
            "list_objects_v2",
            {
                "Contents": [
                    {"Key": key, "Size": 1, "ETag": "fixture", "LastModified": NOW} for key in keys
                ]
            },
            {"Bucket": "fixture"},
        )
        assert set(backup.inventory(s3, "fixture", HEALTH_PROBE_KEYS)) == {
            "raw/fixture.csv",
            "health/user-data.csv",
        }
        stub.assert_no_pending_responses()
