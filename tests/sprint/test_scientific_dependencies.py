"""Keep numerical calculations on the declared, shared service runtime."""

from importlib.metadata import version
from pathlib import Path

import pytest
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[2]


def requirements(path: str) -> dict[str, Requirement]:
    return {
        requirement.name: requirement
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith(("#", "-"))
        for requirement in [Requirement(line)]
    }


@pytest.mark.parametrize("name", ["numpy", "scipy"])
def test_api_and_quant_worker_share_exact_numeric_versions(name: str) -> None:
    api = requirements("services/api/requirements.txt")[name]
    worker = requirements("services/worker-quant/requirements.txt")[name]
    assert str(api.specifier) == str(worker.specifier)
    pins = list(api.specifier)
    assert len(pins) == 1 and pins[0].operator == "=="
    assert version(name) in api.specifier


def test_scipy_stubs_target_the_installed_runtime_release() -> None:
    runtime = version("scipy").split(".")[:3]
    stub = version("scipy-stubs").split(".")[:3]
    assert runtime == stub
