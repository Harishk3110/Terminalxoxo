from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import check_python_types as gate


def test_git_inventory_includes_new_sources_and_stubs_but_not_runtime_data(
    tmp_path: Path,
) -> None:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    for name in (
        "scripts/check.py",
        "typings/vendor.pyi",
        "logs/runtime.py",
        "services/api/app.py",
    ):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
    assert [path.as_posix() for path in gate.inventory(tmp_path)] == [
        "scripts/check.py",
        "services/api/app.py",
        "typings/vendor.pyi",
    ]


@pytest.mark.parametrize(
    "left,right",
    [
        ("services/local-agent/agent.py", "services/broker-agent/agent/main.py"),
        ("services/api/app/main.py", "services/worker-data/app/main.py"),
        ("services/worker-data/app/main.py", "services/worker-quant/app/main.py"),
        ("services/api/tests/conftest.py", "tests/sprint/conftest.py"),
    ],
)
def test_independent_module_names_remain_in_separate_groups(left: str, right: str) -> None:
    assert gate.distribution(Path(left)) != gate.distribution(Path(right))


def test_inventory_only_never_reports_a_passing_type_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gate, "inventory", lambda _: [Path("scripts/example.py")])
    monkeypatch.setattr(sys, "argv", ["check", "--inventory-only", "--output", str(tmp_path)])
    assert gate.main() == 0
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "NOT_RUN"
    assert manifest["source_files"] == 1
    assert manifest["groups"][0]["status"] == "NOT_RUN"
    assert "--strict" in manifest["groups"][0]["command"]
    assert "--explicit-package-bases" in manifest["groups"][0]["command"]


def test_empty_inventory_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(gate, "inventory", lambda _: [])
    monkeypatch.setattr(sys, "argv", ["check", "--inventory-only"])
    with pytest.raises(RuntimeError, match="empty type gate"):
        gate.main()


@pytest.mark.parametrize("group", ["tests/sprint", "services/api/tests"])
def test_sibling_test_imports_are_checked_in_their_own_distribution(
    group: str, tmp_path: Path
) -> None:
    directory = tmp_path / group
    directory.mkdir(parents=True)
    helper = directory / "test_helper.py"
    helper.write_text("value: int = 1\n", encoding="utf-8")
    consumer = directory / "test_consumer.py"
    consumer.write_text("from test_helper import value\nwrong: str = value\n", encoding="utf-8")
    env = gate.type_environment(group, tmp_path)
    paths = env["MYPYPATH"].split(os.pathsep)
    assert paths[-1] == str(directory)
    assert len(paths) == 3
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--explicit-package-bases",
            str(helper),
            str(consumer),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "Incompatible types in assignment" in result.stdout
    assert "import-not-found" not in result.stdout
    assert "Source file found twice" not in result.stdout
    consumer.write_text("from test_helper import value\nvalid: int = value\n", encoding="utf-8")
    fixed = subprocess.run(
        [
            sys.executable,
            "-m",
            "mypy",
            "--strict",
            "--explicit-package-bases",
            str(helper),
            str(consumer),
        ],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert fixed.returncode == 0, fixed.stdout


def test_runtime_groups_do_not_import_test_directories(tmp_path: Path) -> None:
    paths = gate.type_environment("services/api/app", tmp_path)["MYPYPATH"].split(os.pathsep)
    assert paths == [str(tmp_path / "typings"), str(tmp_path / "services/api")]


def test_failed_distribution_is_not_converted_into_a_warning(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(gate, "inventory", lambda _: [Path("scripts/example.py")])
    monkeypatch.setattr(sys, "argv", ["check", "--output", str(tmp_path)])

    def fail(*args: object, **kwargs: object) -> subprocess.CompletedProcess[bytes]:
        environment = kwargs["env"]
        assert isinstance(environment, dict) and environment["PYTHONHASHSEED"] == "0"
        return subprocess.CompletedProcess(["mypy"], 1, b"example.py:1: error: fixture\n")

    monkeypatch.setattr(subprocess, "run", fail)
    assert gate.main() == 1
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "FAIL"
    assert manifest["groups"][0]["exit_code"] == 1
    assert "fixture" in Path(manifest["groups"][0]["log"]).read_text()
