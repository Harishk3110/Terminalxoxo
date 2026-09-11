import hashlib
import json
import os
import sys
from pathlib import Path

import pytest

from scripts.release_candidate import Command, execute
from scripts.release_results import validate_results


@pytest.mark.parametrize(
    "content",
    [
        '<testsuites><testsuite tests="1"><testcase name="executed"/></testsuite></testsuites>',
        '<testsuite tests="2" failures="0" errors="0" skipped="0"><testcase/><testcase/></testsuite>',
    ],
)
def test_only_nonempty_executed_junit_receipts_pass(tmp_path: Path, content: str) -> None:
    path = tmp_path / "tests.xml"
    path.write_text(content, encoding="utf-8")
    assert validate_results(path) == hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.mark.parametrize(
    "content",
    [
        "<testsuites/>",
        '<testsuite tests="0"/>',
        '<testsuite tests="1"><testcase><skipped/></testcase></testsuite>',
        '<testsuite tests="1"><testcase><failure/></testcase></testsuite>',
        '<testsuite tests="1"><testcase><error/></testcase></testsuite>',
        '<testsuite tests="1" errors="1"><testcase/></testsuite>',
        '<testsuite tests="2"><testcase/></testsuite>',
        '<testsuite tests="one"><testcase/></testsuite>',
        "<testcase/>",
        "<not-valid",
    ],
)
def test_empty_skipped_failed_or_inconsistent_junit_is_rejected(
    tmp_path: Path, content: str
) -> None:
    path = tmp_path / "tests.xml"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        validate_results(path)


@pytest.mark.parametrize(
    "changes",
    [
        {"expected": 0},
        {"skipped": 1},
        {"unexpected": 1},
        {"flaky": 1},
        {"expected": "1"},
    ],
)
def test_browser_zero_tests_skips_retries_and_failures_cannot_pass(
    tmp_path: Path, changes: dict[str, object]
) -> None:
    path = tmp_path / "browser.json"
    path.write_text(
        json.dumps(
            {
                "stats": {"expected": 1, "skipped": 0, "unexpected": 0, "flaky": 0, **changes},
                "errors": [],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        validate_results(path)


def test_browser_report_requires_error_free_completed_statistics(tmp_path: Path) -> None:
    path = tmp_path / "browser.json"
    payload: dict[str, object] = {
        "stats": {"expected": 37, "skipped": 0, "unexpected": 0, "flaky": 0},
        "errors": [],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert validate_results(path) == hashlib.sha256(path.read_bytes()).hexdigest()
    payload["errors"] = [{"message": "global teardown failed"}]
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ValueError):
        validate_results(path)


def test_zero_exit_with_skipped_tests_still_fails_the_gate(tmp_path: Path) -> None:
    report = tmp_path / "tests.xml"
    report.write_text(
        '<testsuite tests="1"><testcase><skipped/></testcase></testsuite>', encoding="utf-8"
    )
    command = Command((sys.executable, "-c", "print('process returned zero')"), result_file=report)
    assert execute(command, tmp_path / "command.log", os.environ) == 1
    assert "Test receipt rejected" in (tmp_path / "command.log").read_text()


def test_missing_receipt_never_passes_despite_zero_process_exit(tmp_path: Path) -> None:
    command = Command(
        (sys.executable, "-c", "print('process returned zero')"),
        result_file=tmp_path / "absent.xml",
    )
    assert execute(command, tmp_path / "command.log", os.environ) == 1
