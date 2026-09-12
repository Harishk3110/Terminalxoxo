"""Run one fail-fast, non-destructive local release checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO, Literal
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
PYTHON_ROOTS = (
    "services",
    "packages",
    "scripts",
    "tests",
    "typings",
    "infrastructure",
    "migrations",
)


@dataclass(frozen=True)
class Command:
    argv: tuple[str, ...]
    cwd: Path = ROOT
    test_environment: bool = False
    timeout: int = 1800
    environment: Mapping[str, str] = field(default_factory=dict)
    result_file: Path | None = None


@dataclass(frozen=True)
class Gate:
    name: str
    commands: tuple[Command, ...]


@dataclass
class CommandResult:
    argv: tuple[str, ...]
    cwd: str
    log: str
    started_at: str
    finished_at: str | None = None
    exit_code: int | None = None
    sha256: str | None = None
    result_file: str | None = None
    result_sha256: str | None = None


@dataclass
class Result:
    number: int
    name: str
    state: Literal["NOT_RUN", "RUNNING", "PASS", "FAIL"] = "NOT_RUN"
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    failed_command: str | None = None
    failure_reason: str | None = None
    logs: list[str] = field(default_factory=list)
    commands: list[CommandResult] = field(default_factory=list)


def command_text(command: Command) -> str:
    return subprocess.list2cmdline(command.argv) if os.name == "nt" else shlex.join(command.argv)


def source_fingerprint(root: Path) -> str:
    names = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=root
    ).split(b"\0")
    digest = hashlib.sha256()
    for name in sorted(set(names) - {b""}):
        path = root / os.fsdecode(name)
        digest.update(name + b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest() if path.is_file() else b"MISSING")
    return digest.hexdigest()


def stop_process_tree(process: subprocess.Popen[bytes], stream: BinaryIO) -> None:
    if sys.platform == "win32":
        # Only the process created for this gate and its descendants are targeted.
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.kill()
    process.wait(timeout=10)


def execute(command: Command, log: Path, environment: Mapping[str, str]) -> int:
    with log.open("xb") as stream:
        try:
            process = subprocess.Popen(
                command.argv,
                cwd=command.cwd,
                env={**environment, **command.environment},
                stdout=stream,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                start_new_session=os.name != "nt",
            )
        except OSError as error:
            stream.write(f"\nCommand could not start ({type(error).__name__}).\n".encode())
            return 127
        try:
            code = process.wait(timeout=command.timeout)
            if code == 0 and command.result_file is not None:
                from scripts.release_results import validate_results

                try:
                    validate_results(command.result_file)
                except (ValueError, OSError) as error:
                    stream.write(
                        f"\nTest receipt rejected ({type(error).__name__}); no pass recorded.\n".encode()
                    )
                    return 1
            return code
        except subprocess.TimeoutExpired:
            stop_process_tree(process, stream)
            stream.write(b"\nRelease command exceeded its bounded timeout.\n")
            return 124
        except KeyboardInterrupt:
            stop_process_tree(process, stream)
            raise


def run_gates(
    gates: Sequence[Gate],
    output: Path,
    host_environment: Mapping[str, str],
    test_environment: Mapping[str, str],
    fingerprint: Callable[[], str],
    executor: Callable[[Command, Path, Mapping[str, str]], int] = execute,
) -> int:
    if not gates or any(not gate.commands for gate in gates):
        raise ValueError("A release gate cannot be empty")
    output.mkdir(parents=True, exist_ok=False)
    original: str | None = None
    results = [Result(index, gate.name) for index, gate in enumerate(gates, 1)]
    manifest = output / "manifest.json"

    def record() -> None:
        pending = manifest.with_suffix(".pending")
        pending.write_text(
            json.dumps(
                {
                    "source_sha256": original,
                    "observed_at": datetime.now(UTC).isoformat(),
                    "commit": host_environment.get("KNK_RELEASE_COMMIT", "UNRECORDED"),
                    "branch": host_environment.get("KNK_RELEASE_BRANCH", "UNRECORDED"),
                    "state": "PASS"
                    if all(row.state == "PASS" for row in results)
                    else "FAIL"
                    if any(row.state == "FAIL" for row in results)
                    else "INCOMPLETE",
                    "gates": [asdict(row) for row in results],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        pending.replace(manifest)

    record()
    for gate, result in zip(gates, results, strict=True):
        result.started_at = datetime.now(UTC).isoformat()
        result.state = "RUNNING"
        record()
        try:
            if original is None:
                original = fingerprint()
            for index, command in enumerate(gate.commands, 1):
                display = command_text(command)
                result.failed_command = display
                if fingerprint() != original:
                    raise RuntimeError("Source changed during release; start a new checkpoint")
                print(f"[{result.number:02d}/{len(gates):02d}] {gate.name}: {display}", flush=True)
                log = output / f"{result.number:02d}-{index:02d}.log"
                result.logs.append(str(log))
                receipt = CommandResult(
                    command.argv,
                    str(command.cwd),
                    str(log),
                    datetime.now(UTC).isoformat(),
                    result_file=str(command.result_file)
                    if command.result_file is not None
                    else None,
                )
                result.commands.append(receipt)
                record()
                code = executor(
                    command, log, test_environment if command.test_environment else host_environment
                )
                result.exit_code = code
                receipt.exit_code = code
                receipt.finished_at = datetime.now(UTC).isoformat()
                receipt.sha256 = hashlib.sha256(log.read_bytes()).hexdigest()
                if command.result_file is not None and command.result_file.is_file():
                    receipt.result_sha256 = hashlib.sha256(
                        command.result_file.read_bytes()
                    ).hexdigest()
                if code != 0:
                    result.state = "FAIL"
                    result.failure_reason = f"Command returned exit code {code}"
                    print(f"FAILED ({code}), cwd={command.cwd}: {display}\nLog: {log}", flush=True)
                    return code
                if fingerprint() != original:
                    raise RuntimeError("Source changed during release; start a new checkpoint")
            result.failed_command = None
            result.state = "PASS"
        except (RuntimeError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as error:
            result.state = "FAIL"
            result.exit_code = 130 if isinstance(error, KeyboardInterrupt) else 1
            result.failure_reason = (
                str(error) if isinstance(error, RuntimeError) else type(error).__name__
            )
            print(
                f"FAILED: {gate.name} ({result.failure_reason}): {result.failed_command}",
                flush=True,
            )
            return result.exit_code
        finally:
            result.finished_at = datetime.now(UTC).isoformat()
            record()
    return 0


def release_gates(output: Path, env_file: Path, pg_container: str) -> list[Gate]:
    python = sys.executable
    corepack = shutil.which("corepack.cmd" if os.name == "nt" else "corepack") or "corepack"
    pnpm = (corepack, "pnpm")
    compose = ("docker", "compose", "--env-file", str(env_file))
    helper = (python, "-m", "scripts.release_checks")

    def py(*args: str, test: bool = False, report: str | None = None) -> Command:
        result_file = output / report if report else None
        argv = (python, *args)
        if result_file is not None:
            argv += ("--junitxml", str(result_file))
        return Command(argv, test_environment=test, result_file=result_file)

    def check(action: str) -> Command:
        return Command(
            (
                *helper,
                action,
                "--output",
                str(output),
                "--env-file",
                str(env_file),
                "--pg-container",
                pg_container,
            )
        )

    return [
        Gate("Environment validation", (check("environment"),)),
        Gate("Secret scan", (py("scripts/scan_release_secrets.py"),)),
        Gate("No-execution scan", (Command(("node", "tests/security/no-execution-methods.mjs")),)),
        Gate(
            "Dependency installation check",
            (py("-m", "pip", "check"), Command((*pnpm, "install", "--frozen-lockfile"))),
        ),
        Gate(
            "Database migration upgrade",
            (
                py(
                    "-m",
                    "pytest",
                    "tests/sprint/test_ledger_migrations.py",
                    "-k",
                    "not downgrade",
                    "--basetemp",
                    str(output / "migration-upgrade"),
                    "-q",
                    test=True,
                    report="migration-upgrade.xml",
                ),
            ),
        ),
        Gate(
            "Database downgrade/upgrade test",
            (
                py(
                    "-m",
                    "pytest",
                    "tests/sprint/test_ledger_migrations.py::test_upgrade_downgrade_upgrade_preserves_existing_portfolio_rows",
                    "tests/integration/test_postgres_lifecycle.py::test_postgres_latest_downgrade_upgrade_retains_existing_book",
                    "--basetemp",
                    str(output / "migration-roundtrip"),
                    "-q",
                    test=True,
                    report="migration-roundtrip.xml",
                ),
            ),
        ),
        Gate("Backend formatting", (py("-m", "ruff", "format", "--check", *PYTHON_ROOTS),)),
        Gate("Ruff", (py("-m", "ruff", "check", *PYTHON_ROOTS),)),
        Gate(
            "Strict first-party mypy",
            (py("scripts/check_python_types.py", "--output", str(output / "types")),),
        ),
        Gate(
            "Backend unit tests",
            (
                py(
                    "-m",
                    "pytest",
                    "tests/sprint",
                    "--cov=services/api/app",
                    "--cov-report=term",
                    "-q",
                    test=True,
                    report="backend-unit.xml",
                ),
            ),
        ),
        Gate(
            "Backend integration tests",
            (
                py(
                    "-m",
                    "pytest",
                    "services/api/tests",
                    "tests/integration/test_managed_backup.py",
                    "tests/integration/test_excel_dcf.py",
                    "tests/integration/test_postgres_lifecycle.py::test_postgres_analysis_transitions_preserve_the_committed_winner",
                    "--cov=services/api/app",
                    "--cov-append",
                    "--cov-report=term",
                    "-q",
                    test=True,
                    report="backend-integration.xml",
                ),
            ),
        ),
        Gate("Coverage", (py("-m", "coverage", "report", "--fail-under=86.58", test=True),)),
        Gate("Frontend lint", (Command((*pnpm, "lint")),)),
        Gate("TypeScript", (Command((*pnpm, "typecheck")),)),
        Gate(
            "Frontend unit tests",
            (
                Command(
                    (
                        *pnpm,
                        "dlx",
                        "node@22",
                        str(ROOT / "node_modules/vitest/vitest.mjs"),
                        "run",
                        "tests",
                        "--reporter=default",
                        "--reporter=junit",
                        f"--outputFile={output / 'frontend-unit.xml'}",
                    ),
                    cwd=ROOT / "apps/terminal-web",
                    result_file=output / "frontend-unit.xml",
                ),
            ),
        ),
        Gate(
            "Shared package tests",
            (
                Command(
                    (
                        *pnpm,
                        "dlx",
                        "node@22",
                        str(ROOT / "node_modules/vitest/vitest.mjs"),
                        "run",
                        "packages",
                        "--reporter=default",
                        "--reporter=junit",
                        f"--outputFile={output / 'shared-unit.xml'}",
                    ),
                    result_file=output / "shared-unit.xml",
                ),
            ),
        ),
        Gate(
            "Frontend build",
            (
                Command(
                    (*pnpm, "dlx", "node@22", "node_modules/next/dist/bin/next", "build"),
                    cwd=ROOT / "apps/terminal-web",
                    environment={
                        "NEXT_PUBLIC_APP_ENV": "test",
                        "KNK_API_URL": "http://127.0.0.1:8001",
                    },
                ),
            ),
        ),
        Gate("Docker build", (Command((*compose, "build"), timeout=3600),)),
        Gate(
            "Docker startup",
            (Command((*compose, "up", "-d", "--no-build", "--wait", "--wait-timeout", "240")),),
        ),
        Gate(
            "Health checks",
            (
                py(
                    "scripts/overnight_watchdog.py",
                    "--once",
                    "--observe-only",
                    "--env-file",
                    str(env_file),
                ),
            ),
        ),
        Gate(
            "Report generation smoke",
            (
                Command(
                    (
                        *compose,
                        "exec",
                        "-T",
                        "api",
                        "python",
                        "scripts/report_smoke.py",
                        "--isolated-postgres",
                    )
                ),
            ),
        ),
        Gate(
            "Full Playwright suite",
            (
                Command(
                    (*pnpm, "exec", "playwright", "test", "--workers=1", "--retries=0"),
                    environment={
                        "PLAYWRIGHT_RUN_ID": output.name + "-full",
                        "PLAYWRIGHT_PYTHON": python,
                        "PLAYWRIGHT_JSON_OUTPUT_FILE": str(output / "browser-full.json"),
                        "PLAYWRIGHT_OUTPUT_DIR": str(output / "browser-full"),
                    },
                    result_file=output / "browser-full.json",
                ),
            ),
        ),
        Gate(
            "Visual comparison",
            (
                Command(
                    (
                        *pnpm,
                        "exec",
                        "playwright",
                        "test",
                        "tests/e2e/terminal.spec.ts",
                        "--grep",
                        "visual workspace|mobile monitoring",
                        "--workers=1",
                        "--retries=0",
                    ),
                    environment={
                        "PLAYWRIGHT_RUN_ID": output.name + "-visual",
                        "PLAYWRIGHT_PYTHON": python,
                        "KNK_COMPARE_SCREENSHOTS": "1",
                        "PLAYWRIGHT_JSON_OUTPUT_FILE": str(output / "browser-visual.json"),
                        "PLAYWRIGHT_OUTPUT_DIR": str(output / "browser-visual"),
                    },
                    result_file=output / "browser-visual.json",
                ),
            ),
        ),
        Gate(
            "Security tests",
            (
                py(
                    "-m",
                    "pytest",
                    "tests/sprint/test_auth_enrollment.py",
                    "services/api/tests/test_terminal_only_security.py",
                    "services/api/tests/test_no_execution_strings.py",
                    "-q",
                    test=True,
                    report="security.xml",
                ),
            ),
        ),
        Gate("Backup", (check("backup"),)),
        Gate("Backup verification", (check("verify"),)),
        Gate("Isolated restore", (check("restore-test"),)),
        Gate(
            "API and worker persistence smoke",
            (
                py(
                    "-m",
                    "pytest",
                    "tests/integration/test_postgres_lifecycle.py::test_api_and_worker_restart_preserve_ledger_nav_and_private_report",
                    "--basetemp",
                    str(output / "persistence"),
                    "-q",
                    test=True,
                    report="persistence.xml",
                ),
            ),
        ),
        Gate("Build evidence", (check("evidence"),)),
    ]


def main() -> int:
    from dotenv import dotenv_values

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env.compose.local")
    parser.add_argument("--pg-container", default="knk-final-local-postgres-1")
    parser.add_argument("--acknowledge-unencrypted", action="store_true")
    parser.add_argument(
        "--list", action="store_true", help="List commands without executing or claiming a pass"
    )
    args = parser.parse_args()
    output = (
        ROOT
        / "logs/release-candidate"
        / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8])
    )
    env_file = args.env_file.resolve()
    gates = release_gates(output, env_file, args.pg_container)
    if args.list:
        for index, gate in enumerate(gates, 1):
            print(
                f"{index:02d}. {gate.name}: "
                + " ; ".join(command_text(command) for command in gate.commands)
            )
        return 0
    environment = dict(os.environ)
    for key in dotenv_values(env_file) if env_file.is_file() else ():
        environment.pop(key, None)
    environment["KNK_RELEASE_BACKUP_ACK"] = "1" if args.acknowledge_unencrypted else "0"
    environment["KNK_RELEASE_COMMIT"] = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    environment["KNK_RELEASE_BRANCH"] = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True
    ).strip()
    test_environment = {
        **environment,
        "KNK_ENV": "local-demo",
        "DATABASE_URL": f"sqlite:///{output.as_posix()}/tests.db",
        "OBJECT_STORAGE_LOCAL_DIR": str(output / "objects"),
        "COVERAGE_FILE": str(output / ".coverage"),
        "KNK_MANAGED_BACKUP_TEST_ENV": str(env_file),
        "KNK_TEST_PG_TOOLS_CONTAINER": args.pg_container,
        "KNK_EXCEL_INTEGRATION": "1",
    }
    return run_gates(gates, output, environment, test_environment, lambda: source_fingerprint(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
