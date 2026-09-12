"""Local-only stateful release checks; no credentials are written to evidence."""

import argparse
import hashlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError

from scripts.release_candidate import release_gates
from scripts.release_results import validate_results

ROOT = Path(__file__).resolve().parents[1]


class BackupReceipt(BaseModel):
    archive: str = Field(pattern=r"^knk-postgres-[A-Za-z0-9-]+\.zip$")
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class LocalConfigurationError(ValueError):
    """Only fixed, non-secret diagnostics may use this exception."""


class CommandEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    argv: list[str] = Field(min_length=1)
    cwd: str
    log: str
    started_at: datetime
    finished_at: datetime
    exit_code: Literal[0]
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    result_file: str | None
    result_sha256: str | None = Field(pattern=r"^[0-9a-f]{64}$")


class GateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    number: int
    name: str
    state: Literal["PASS"]
    started_at: datetime
    finished_at: datetime
    exit_code: Literal[0]
    failed_command: None
    failure_reason: None
    logs: list[str]
    commands: list[CommandEvidence] = Field(min_length=1)


class ManifestEvidence(BaseModel):
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: datetime
    commit: str = Field(pattern=r"^[0-9a-f]{40}$")
    branch: str = Field(min_length=1)
    state: Literal["INCOMPLETE"]
    # The last gate is actively writing this evidence, not already passed.
    gates: list[dict[str, object]] = Field(min_length=29, max_length=29)


def local_configuration(env_file: Path) -> None:
    if sys.version_info[:2] != (3, 12):
        raise LocalConfigurationError("Release verification requires Python 3.12")
    if not env_file.is_file() or not (ROOT / "apps/terminal-web/package.json").is_file():
        raise LocalConfigurationError(
            "Existing local environment and terminal workspace are required"
        )
    values = dotenv_values(env_file)
    if values.get("KNK_ENV") != "local-demo":
        raise LocalConfigurationError(
            "This release runner targets the existing local-demo stack, not a production book"
        )
    try:
        url = make_url(values.get("DATABASE_URL") or "")
    except ArgumentError:
        raise LocalConfigurationError("A valid local PostgreSQL URL is required") from None
    if url.get_backend_name() != "postgresql" or url.host not in {
        "postgres",
        "localhost",
        "127.0.0.1",
    }:
        raise LocalConfigurationError("The release backup must target local PostgreSQL")
    if urlparse(values.get("MINIO_ENDPOINT") or "").hostname not in {
        "minio",
        "localhost",
        "127.0.0.1",
    }:
        raise LocalConfigurationError("The release backup must target local private object storage")
    if os.environ.get("KNK_RELEASE_BACKUP_ACK") != "1":
        raise LocalConfigurationError(
            "Use --acknowledge-unencrypted: local backups contain private data and database credentials"
        )


def environment(env_file: Path) -> None:
    local_configuration(env_file)
    subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], check=True, timeout=30)
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True, timeout=30)
    print("Existing local environment validated; no secrets printed")


def backup(action: str, output: Path, env_file: Path, pg_container: str) -> None:
    if action not in {"backup", "verify", "restore-test"}:
        raise ValueError("Unknown backup action")
    local_configuration(env_file)
    destination = output / "backup"
    args = [sys.executable, "-m", "infrastructure.scripts.managed_backup", action]
    if action == "backup":
        args.extend(("--destination", str(destination)))
    else:
        receipt = BackupReceipt.model_validate_json(
            (destination / "latest-backup.json").read_bytes()
        )
        archive = destination / receipt.archive
        if archive.is_symlink() or archive.resolve().parent != destination.resolve():
            raise ValueError("Backup archive must remain inside this checkpoint")
        with archive.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != receipt.sha256:
                raise ValueError("Backup archive no longer matches the checkpoint receipt")
        args.extend(("--archive", str(archive)))
        if action == "restore-test":
            args.extend(("--sha256", receipt.sha256, "--acknowledge-trusted-source"))
    if action != "verify":
        if os.environ.get("KNK_RELEASE_BACKUP_ACK") != "1":
            raise ValueError("Unencrypted private-backup acknowledgement is required")
        args.extend(
            (
                "--env-file",
                str(env_file),
                "--database-host",
                "127.0.0.1",
                "--s3-endpoint",
                "http://127.0.0.1:9000",
                "--pg-tools-container",
                pg_container,
                "--acknowledge-unencrypted",
            )
        )
    subprocess.run(args, cwd=ROOT, check=True, timeout=1800)


def evidence(output: Path, env_file: Path, pg_container: str) -> None:
    import json

    payload = ManifestEvidence.model_validate_json((output / "manifest.json").read_bytes())
    expected = release_gates(output, env_file, pg_container)
    rows = [GateEvidence.model_validate_json(json.dumps(row)) for row in payload.gates[:-1]]
    pending = payload.gates[-1]
    if (pending.get("number"), pending.get("name"), pending.get("state")) != (
        len(expected),
        expected[-1].name,
        "RUNNING",
    ):
        raise ValueError("Evidence gate is not running")
    for index, (row, gate) in enumerate(zip(rows, expected[:-1], strict=True), 1):
        if (row.number, row.name, len(row.commands)) != (index, gate.name, len(gate.commands)):
            raise ValueError("Gate does not match the release contract")
        if row.logs != [command.log for command in row.commands]:
            raise ValueError("Command logs do not match gate receipt")
        if row.finished_at < row.started_at:
            raise ValueError("Invalid gate timestamps")
        for command_index, (command, definition) in enumerate(
            zip(row.commands, gate.commands, strict=True), 1
        ):
            log = output / f"{index:02d}-{command_index:02d}.log"
            if command.argv != list(definition.argv) or command.cwd != str(definition.cwd):
                raise ValueError("Executed command does not match release contract")
            if command.log != str(log) or log.is_symlink():
                raise ValueError("Evidence log must belong to this checkpoint")
            if not row.started_at <= command.started_at <= command.finished_at <= row.finished_at:
                raise ValueError("Invalid command timestamps")
            if hashlib.sha256(log.read_bytes()).hexdigest() != command.sha256:
                raise ValueError("Evidence log changed after execution")
            if definition.result_file is not None:
                if command.result_file != str(definition.result_file):
                    raise ValueError("Test result receipt does not match the gate")
                if validate_results(definition.result_file) != command.result_sha256:
                    raise ValueError("Test result receipt changed after execution")
            elif command.result_file is not None or command.result_sha256 is not None:
                raise ValueError("Unexpected test result receipt")
    lines = ["# Release Checkpoint", "", "Source SHA-256: " + payload.source_sha256, ""]
    lines.extend(
        f"- {row.number:02d}. {row.name}: {row.state} (exit {row.exit_code})" for row in rows
    )
    (output / "BUILD_EVIDENCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(
        "Evidence written; this command does not certify untested domain or hosted-deployment requirements"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["environment", "backup", "verify", "restore-test", "evidence"]
    )
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--pg-container", required=True)
    args = parser.parse_args()
    try:
        if args.action == "environment":
            environment(args.env_file)
        elif args.action == "evidence":
            evidence(args.output, args.env_file, args.pg_container)
        else:
            backup(args.action, args.output, args.env_file, args.pg_container)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        if isinstance(error, LocalConfigurationError):
            print(str(error))
        else:
            print(
                f"Release check failed ({type(error).__name__}); private connection details redacted"
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
