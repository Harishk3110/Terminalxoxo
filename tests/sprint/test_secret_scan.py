"""Only the exact documented public dummy value may bypass assignment detection."""

import subprocess
from pathlib import Path

import pytest

from scripts import scan_release_secrets as scanner


@pytest.mark.parametrize(
    "name,key,value,allowed",
    [
        (
            "tests/sprint/test_provider_connections.py",
            "MARKET_DATA_API_KEY",
            '"server-secret",',
            True,
        ),
        (
            "tests/sprint/test_provider_connections.py",
            "MARKET_DATA_API_KEY",
            '"unexpected-credential",',
            False,
        ),
        ("services/api/app/config.py", "MARKET_DATA_API_KEY", '"server-secret",', False),
        ("tests/sprint/test_provider_connections.py", "OTHER_API_KEY", '"server-secret",', False),
        (
            "tests/sprint/test_provider_connections.py",
            "MARKET_DATA_API_KEY",
            "secret_variable,",
            False,
        ),
        (
            "tests/sprint/test_provider_connections.py",
            "MARKET_DATA_API_KEY",
            '["server-secret"],',
            False,
        ),
        (
            "tests/sprint/test_provider_connections.py",
            "MARKET_DATA_API_KEY",
            '"server-secret" + "other",',
            False,
        ),
    ],
)
def test_fixture_exception_requires_exact_path_key_and_literal(
    name: str, key: str, value: str, allowed: bool
) -> None:
    assert scanner.public_fixture(name, key, value) is allowed


@pytest.mark.parametrize("unexpected", [False, True])
def test_scan_keeps_unexpected_credentials_blocking_and_redacted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    unexpected: bool,
) -> None:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    path = tmp_path / "tests/sprint/test_provider_connections.py"
    path.parent.mkdir(parents=True)
    value = "unexpected-credential" if unexpected else "server-secret"
    path.write_text(f'MARKET_DATA_API_KEY="{value}",\n', encoding="utf-8")
    monkeypatch.setattr(scanner, "ROOT", tmp_path)
    assert scanner.main() == int(unexpected)
    output = capsys.readouterr().out
    assert value not in output
    assert ("nonempty credential assignment" in output) is unexpected


def test_token_detection_still_applies_to_an_allowed_fixture_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    subprocess.run(["git", "init", "--quiet", str(tmp_path)], check=True)
    path = tmp_path / "tests/sprint/test_provider_connections.py"
    path.parent.mkdir(parents=True)
    token_shape = "gh" + "p_" + "a" * 30
    path.write_text(f'TOKEN="{token_shape}"\n', encoding="utf-8")
    monkeypatch.setattr(scanner, "ROOT", tmp_path)
    assert scanner.main() == 1
    output = capsys.readouterr().out
    assert "possible credential or private key" in output
    assert token_shape not in output
