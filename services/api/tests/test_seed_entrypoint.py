import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("compact_layout", [False, True])
def test_seed_entrypoint_outside_repository_cwd(tmp_path: Path, compact_layout: bool) -> None:
    service_root = Path(__file__).resolve().parents[1]
    script = service_root / "scripts" / "seed_demo.py"
    if compact_layout:
        service_copy = tmp_path / "service"
        (service_copy / "scripts").mkdir(parents=True)
        shutil.copytree(
            service_root / "app", service_copy / "app", ignore=shutil.ignore_patterns("__pycache__")
        )
        script = Path(shutil.copy2(script, service_copy / "scripts"))
    env = {key: value for key, value in os.environ.items() if key != "PYTHONPATH"}
    env["DATABASE_URL"] = f"sqlite:///{(tmp_path / 'unconfigured' / 'ledger.db').as_posix()}"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "--reset" in result.stdout
    assert not (tmp_path / "unconfigured").exists()
