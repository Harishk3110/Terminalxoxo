"""Release orchestration must fail closed without touching the active stack."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from collections.abc import Mapping
from pathlib import Path

import pytest

from scripts import release_candidate as runner
from scripts import release_checks as checks

SOURCE = "a" * 64
HOST = {"KNK_RELEASE_COMMIT": "b" * 40, "KNK_RELEASE_BRANCH": "test-checkpoint"}


def recorded_success(command: runner.Command, log: Path, environment: Mapping[str, str]) -> int:
    log.write_text("verified test command\n", encoding="utf-8")
    if command.result_file is not None:
        command.result_file.write_text(
            '<testsuites><testsuite tests="1"><testcase name="synthetic-runner-fixture"/></testsuite></testsuites>'
            if command.result_file.suffix == ".xml"
            else json.dumps(
                {
                    "stats": {"expected": 1, "skipped": 0, "unexpected": 0, "flaky": 0},
                    "errors": [],
                }
            ),
            encoding="utf-8",
        )
    return 0


def test_release_contract_is_ordered_nonempty_and_non_destructive(tmp_path: Path) -> None:
    gates = runner.release_gates(tmp_path, tmp_path / "private.env", "test-postgres")
    assert len(gates) == 27
    assert all(gate.commands for gate in gates)
    assert [gate.name for gate in gates][0:7] == [
        "Environment validation",
        "Secret scan",
        "Dependency installation check",
        "Database migration check",
        "Backend formatting",
        "Ruff",
        "Strict first-party mypy",
    ]
    assert [gate.name for gate in gates][-5:] == [
        "Backup",
        "Backup verification",
        "Isolated restore",
        "API and worker persistence smoke",
        "Build evidence",
    ]
    argv = [part for gate in gates for command in gate.commands for part in command.argv]
    assert "--frozen-lockfile" in argv and "--retries=0" in argv
    assert not {"--reset", "--clean", "down", "--force", "--update-snapshots"} & set(argv)
    assert gates[7].commands[0].test_environment
    assert gates[8].commands[0].test_environment
    assert (
        "tests/integration/test_postgres_lifecycle.py::test_postgres_analysis_transitions_preserve_the_committed_winner"
        in gates[8].commands[0].argv
    )
    assert not gates[15].commands[0].test_environment
    full, visual = gates[18].commands[0], gates[19].commands[0]
    assert visual.environment["KNK_COMPARE_SCREENSHOTS"] == "1"
    assert (
        full.environment["PLAYWRIGHT_JSON_OUTPUT_FILE"]
        != visual.environment["PLAYWRIGHT_JSON_OUTPUT_FILE"]
    )
    assert full.environment["PLAYWRIGHT_OUTPUT_DIR"] != visual.environment["PLAYWRIGHT_OUTPUT_DIR"]


def test_success_records_exact_commands_times_and_hashed_logs(tmp_path: Path) -> None:
    output = tmp_path / "run"
    commands = (
        runner.Command((sys.executable, "-c", "print('first')")),
        runner.Command((sys.executable, "-c", "print('second')")),
    )
    assert (
        runner.run_gates(
            [runner.Gate("Executed", commands)], output, os.environ, {}, lambda: SOURCE
        )
        == 0
    )
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["state"] == "PASS" and manifest["source_sha256"] == SOURCE
    row = checks.GateEvidence.model_validate_json(json.dumps(manifest["gates"][0]))
    assert len(row.commands) == 2
    for receipt, definition in zip(row.commands, commands, strict=True):
        assert receipt.argv == list(definition.argv) and receipt.cwd == str(definition.cwd)
        assert receipt.sha256 == hashlib.sha256(Path(receipt.log).read_bytes()).hexdigest()
        assert row.started_at <= receipt.started_at <= receipt.finished_at <= row.finished_at


@pytest.mark.parametrize("fail_at", [0, 1, 2])
def test_first_failure_stops_all_later_commands(tmp_path: Path, fail_at: int) -> None:
    calls: list[str] = []

    def execute(command: runner.Command, log: Path, environment: Mapping[str, str]) -> int:
        calls.append(command.argv[0])
        log.write_text("intentional failing fixture", encoding="utf-8")
        return 19 if len(calls) - 1 == fail_at else 0

    gates = [
        runner.Gate("One", (runner.Command(("first",)), runner.Command(("second",)))),
        runner.Gate("Two", (runner.Command(("third",)),)),
        runner.Gate("Three", (runner.Command(("never",)),)),
    ]
    output = tmp_path / "run"
    assert runner.run_gates(gates, output, HOST, {}, lambda: SOURCE, execute) == 19
    assert len(calls) == fail_at + 1
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["state"] == "FAIL"
    failed = next(row for row in manifest["gates"] if row["state"] == "FAIL")
    assert failed["exit_code"] == 19 and failed["failed_command"] == calls[-1]
    assert manifest["gates"][-1]["state"] == "NOT_RUN"
    assert manifest["gates"][-1]["exit_code"] is None


def test_host_and_isolated_test_environments_are_kept_separate(tmp_path: Path) -> None:
    observed: list[Mapping[str, str]] = []

    def execute(command: runner.Command, log: Path, environment: Mapping[str, str]) -> int:
        observed.append(environment)
        return recorded_success(command, log, environment)

    gates = [
        runner.Gate(
            "Both", (runner.Command(("host",)), runner.Command(("test",), test_environment=True))
        )
    ]
    assert (
        runner.run_gates(
            gates, tmp_path / "run", HOST, {"DATABASE_URL": "isolated"}, lambda: SOURCE, execute
        )
        == 0
    )
    assert observed == [HOST, {"DATABASE_URL": "isolated"}]


@pytest.mark.parametrize("change_at", [2, 3])
def test_source_change_before_or_after_command_is_a_failure(tmp_path: Path, change_at: int) -> None:
    calls = 0

    def fingerprint() -> str:
        nonlocal calls
        calls += 1
        return SOURCE if calls < change_at else "c" * 64

    output = tmp_path / "run"
    gates = [
        runner.Gate("One", (runner.Command(("one",)),)),
        runner.Gate("Two", (runner.Command(("two",)),)),
    ]
    assert runner.run_gates(gates, output, HOST, {}, fingerprint, recorded_success) == 1
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["gates"][0]["state"] == "FAIL"
    assert "Source changed" in manifest["gates"][0]["failure_reason"]
    assert manifest["gates"][1]["state"] == "NOT_RUN"


def test_initial_fingerprint_failure_still_records_a_failed_checkpoint(tmp_path: Path) -> None:
    def unavailable() -> str:
        raise OSError("unavailable")

    output = tmp_path / "run"
    assert (
        runner.run_gates(
            [runner.Gate("One", (runner.Command(("one",)),))], output, HOST, {}, unavailable
        )
        == 1
    )
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["state"] == "FAIL" and manifest["source_sha256"] is None


def test_existing_evidence_and_empty_gates_are_never_overwritten(tmp_path: Path) -> None:
    sentinel = tmp_path / "manifest.json"
    sentinel.write_text("existing evidence", encoding="utf-8")
    gate = runner.Gate("One", (runner.Command(("one",)),))
    with pytest.raises(FileExistsError):
        runner.run_gates([gate], tmp_path, HOST, {}, lambda: SOURCE)
    with pytest.raises(ValueError):
        runner.run_gates([], tmp_path / "empty", HOST, {}, lambda: SOURCE)
    with pytest.raises(ValueError):
        runner.run_gates([runner.Gate("Empty", ())], tmp_path / "empty", HOST, {}, lambda: SOURCE)
    assert sentinel.read_text() == "existing evidence"


def test_missing_executable_returns_127_not_a_pass(tmp_path: Path) -> None:
    log = tmp_path / "missing.log"
    assert (
        runner.execute(runner.Command((str(tmp_path / "nonexistent-executable"),)), log, os.environ)
        == 127
    )
    assert "Command could not start" in log.read_text()


def test_timeout_stops_owned_child_processes(tmp_path: Path) -> None:
    marker = tmp_path / "orphan-wrote.txt"
    child = f"import time; from pathlib import Path; time.sleep(3); Path({str(marker)!r}).touch()"
    parent = f"import subprocess, sys, time; subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(30)"
    command = runner.Command((sys.executable, "-c", parent), timeout=1)
    assert runner.execute(command, tmp_path / "timeout.log", os.environ) == 124
    time.sleep(3)
    assert not marker.exists(), "Timed-out gate left its child process running"


@pytest.fixture
def local_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "fixture.env"
    path.write_text(
        "KNK_ENV=local-demo\nDATABASE_URL=postgresql://fixture:fixture@postgres/fixture\n"
        "MINIO_ENDPOINT=http://minio:9000\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("KNK_RELEASE_BACKUP_ACK", "1")
    return path


@pytest.mark.parametrize(
    "replacement",
    [
        "KNK_ENV=production\n",
        "KNK_ENV=local-demo\nDATABASE_URL=secret-credential-bad-url\n",
        "KNK_ENV=local-demo\nDATABASE_URL=postgresql://fixture:secret-credential@external.example/book\n",
        "KNK_ENV=local-demo\nDATABASE_URL=postgresql://fixture@postgres/book\nMINIO_ENDPOINT=https://external.example\n",
    ],
)
def test_nonlocal_or_invalid_connections_fail_without_leaking_credentials(
    local_env: Path, replacement: str
) -> None:
    local_env.write_text(replacement, encoding="utf-8")
    with pytest.raises(checks.LocalConfigurationError) as error:
        checks.local_configuration(local_env)
    assert "secret-credential" not in str(error.value)


def test_private_backup_requires_acknowledgement(
    local_env: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("KNK_RELEASE_BACKUP_ACK")
    with pytest.raises(checks.LocalConfigurationError, match="acknowledge-unencrypted"):
        checks.backup("backup", tmp_path, local_env, "fixture")


@pytest.mark.parametrize(
    "archive",
    ["../outside.zip", "C:/outside.zip", "knk-postgres-good.zip/evil", "knk-postgres-bad_name.zip"],
)
def test_receipt_rejects_unsafe_archive_paths(archive: str) -> None:
    with pytest.raises(ValueError):
        checks.BackupReceipt(archive=archive, sha256=SOURCE)


def test_archive_hash_is_pinned_before_verify_or_restore(local_env: Path, tmp_path: Path) -> None:
    destination = tmp_path / "backup"
    destination.mkdir()
    receipt = checks.BackupReceipt(archive="knk-postgres-test.zip", sha256=SOURCE)
    (destination / "latest-backup.json").write_text(receipt.model_dump_json(), encoding="utf-8")
    (destination / receipt.archive).write_bytes(b"tampered")
    for action in ("verify", "restore-test"):
        with pytest.raises(ValueError, match="no longer matches"):
            checks.backup(action, tmp_path, local_env, "fixture")


def evidence_fixture(output: Path, env_file: Path) -> None:
    gates = runner.release_gates(output, env_file, "fixture")

    def execute(command: runner.Command, log: Path, environment: Mapping[str, str]) -> int:
        if "evidence" in command.argv:
            # At this instant gate 27 is RUNNING and gates 1-26 have receipts.
            checks.evidence(output, env_file, "fixture")
            raise KeyboardInterrupt
        return recorded_success(command, log, environment)

    assert runner.run_gates(gates, output, HOST, {}, lambda: SOURCE, execute) == 130
    manifest = json.loads((output / "manifest.json").read_text())
    manifest["state"] = "INCOMPLETE"
    manifest["gates"][-1]["state"] = "RUNNING"
    (output / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_evidence_validates_real_contract_and_all_command_logs(tmp_path: Path) -> None:
    output = tmp_path / "run"
    evidence_fixture(output, tmp_path / "fixture.env")
    checks.evidence(output, tmp_path / "fixture.env", "fixture")
    assert "Source SHA-256: " + SOURCE in (output / "BUILD_EVIDENCE.md").read_text()


@pytest.mark.parametrize(
    "mutation",
    [
        "skip",
        "nonzero",
        "no_exit",
        "wrong_command",
        "missing_command",
        "short",
        "duplicate",
        "log_changed",
        "timestamp",
    ],
)
def test_incomplete_or_changed_evidence_cannot_be_certified(tmp_path: Path, mutation: str) -> None:
    output = tmp_path / "run"
    env_file = tmp_path / "fixture.env"
    evidence_fixture(output, env_file)
    manifest = json.loads((output / "manifest.json").read_text())
    row = manifest["gates"][0]
    if mutation == "skip":
        row["state"] = "SKIP"
    elif mutation == "nonzero":
        row["commands"][0]["exit_code"] = 1
    elif mutation == "no_exit":
        row["exit_code"] = None
    elif mutation == "wrong_command":
        row["commands"][0]["argv"] = ["echo", "PASS"]
    elif mutation == "missing_command":
        row["commands"] = []
    elif mutation == "short":
        manifest["gates"].pop(0)
    elif mutation == "duplicate":
        manifest["gates"][1] = row
    elif mutation == "timestamp":
        row["commands"][0]["finished_at"] = "2000-01-01T00:00:00Z"
    else:
        Path(row["commands"][0]["log"]).write_bytes(b"altered after the gate passed")
    (output / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        checks.evidence(output, env_file, "fixture")


def test_powershell_wrapper_lists_without_running_gates() -> None:
    if os.name != "nt":
        pytest.skip("PowerShell launcher is Windows-specific")
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(runner.ROOT / "scripts/release-candidate.ps1"),
            "--list",
        ],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert len(result.stdout.strip().splitlines()) == 27
    assert result.stdout.startswith("01. Environment validation:")
    assert "27. Build evidence:" in result.stdout
