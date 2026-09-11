"""Recovery evidence must not fabricate a database or certify empty inventory."""

import io
import json
import sqlite3
import subprocess
import sys
import urllib.request
from contextlib import closing
from pathlib import Path

import pytest

from infrastructure.scripts import health, verify_portfolio_release
from scripts.verify_local_recovery import snapshot


@pytest.fixture
def database(tmp_path: Path) -> Path:
    path = tmp_path / "ledger #1.sqlite"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE analysis_runs (id TEXT PRIMARY KEY, status TEXT)")
        connection.executemany(
            "INSERT INTO analysis_runs VALUES (?, ?)",
            [("run-1", "QUEUED"), ("run-2", "SUCCEEDED")],
        )
        connection.commit()
    return path


def test_snapshot_reports_unavailable_job_tables_without_inventing_zero(database: Path) -> None:
    result = snapshot(database)
    assert result["tables"]["analysis_runs"]["rows"] == 2
    assert len(result["tables"]["analysis_runs"]["sha256"]) == 64
    assert result["active_jobs"] == {"analysis_runs": 1, "ingestion_jobs": None}


@pytest.mark.parametrize("probe", ["snapshot", "inventory"])
def test_missing_database_is_not_created(tmp_path: Path, probe: str) -> None:
    path = tmp_path / "missing.sqlite"
    with pytest.raises(FileNotFoundError):
        if probe == "snapshot":
            snapshot(path)
        else:
            verify_portfolio_release.inventory(path)
    assert not path.exists()


@pytest.mark.parametrize("probe", ["snapshot", "inventory"])
def test_empty_business_inventory_is_not_accepted(tmp_path: Path, probe: str) -> None:
    path = tmp_path / "empty.sqlite"
    with closing(sqlite3.connect(path)) as connection:
        connection.execute("CREATE TABLE unrelated (id TEXT)")
    with pytest.raises(ValueError, match="business"):
        if probe == "snapshot":
            snapshot(path)
        else:
            verify_portfolio_release.inventory(path)


def test_inventory_preserves_bytes_and_detects_an_actual_row_change(database: Path) -> None:
    original = database.read_bytes()
    before = verify_portfolio_release.inventory(database)
    assert database.read_bytes() == original
    assert len(before["analysis_runs"]) == 2
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE analysis_runs SET status='RUNNING' WHERE id='run-1'")
        connection.commit()
    after = verify_portfolio_release.inventory(database)
    assert before["analysis_runs"]["run-1"] != after["analysis_runs"]["run-1"]
    assert before["analysis_runs"]["run-2"] == after["analysis_runs"]["run-2"]


@pytest.mark.parametrize("body", [b"null", b"[]", b'"ready"', b"true", b'{"status":"starting"}'])
def test_nonready_health_payload_cannot_pass(
    body: bytes, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class Response(io.BytesIO):
        status = 200

    def respond(url: str, timeout: int) -> Response:
        return Response(body if url.endswith("/ready") else b"KnK Capital")

    monkeypatch.setattr(urllib.request, "urlopen", respond)
    with pytest.raises(SystemExit) as result:
        health.main()
    assert result.value.code == 1
    receipt = json.loads(capsys.readouterr().out)
    assert receipt["api"]["state"] == "NOT_READY"
    assert receipt["terminal"]["state"] == "RESPONDING"


def test_health_network_failure_preserves_unavailable_latency(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def unavailable(url: str, timeout: int) -> None:
        raise OSError("Fixture unavailable")

    monkeypatch.setattr(urllib.request, "urlopen", unavailable)
    with pytest.raises(SystemExit) as result:
        health.main()
    assert result.value.code == 1
    receipt = json.loads(capsys.readouterr().out)
    assert all(row == {"state": "OFFLINE", "latency_ms": None} for row in receipt.values())


@pytest.mark.parametrize(
    "reference",
    [None, [], {}, {"unrelated": {}}, {"analysis_runs": []}, {"analysis_runs": {"id": "bad"}}],
)
def test_malformed_reference_is_not_certified(reference: object) -> None:
    with pytest.raises(ValueError, match="inventory"):
        verify_portfolio_release.compare_inventory(reference, {"analysis_runs": {}})


def test_removed_empty_table_is_not_certified() -> None:
    with pytest.raises(ValueError, match="changed or lost"):
        verify_portfolio_release.compare_inventory({"analysis_runs": {}}, {})


def test_new_records_are_permitted_without_changing_existing_records() -> None:
    verify_portfolio_release.compare_inventory(
        {"analysis_runs": {"run-1": "a" * 64}},
        {"analysis_runs": {"run-1": "a" * 64, "run-2": "b" * 64}},
    )


def test_optimized_python_cannot_disable_preservation_checks(
    database: Path, tmp_path: Path
) -> None:
    reference = tmp_path / "before.json"
    reference.write_text(json.dumps({"analysis_runs": {"run-1": "a" * 64}}))
    output = tmp_path / "after.json"
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            verify_portfolio_release.__file__,
            "compare",
            "--database",
            str(database),
            "--before",
            str(reference),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode != 0
    assert "changed or lost existing records" in result.stderr
    assert not output.exists()


def test_inventory_receipt_cannot_overwrite_source_database(
    database: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = database.read_bytes()
    monkeypatch.setattr(
        sys, "argv", ["probe", "inventory", "--database", str(database), "--output", str(database)]
    )
    with pytest.raises(ValueError, match="source database"):
        verify_portfolio_release.main()
    assert database.read_bytes() == original
