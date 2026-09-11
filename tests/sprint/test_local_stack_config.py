from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from dotenv import dotenv_values

from scripts.prepare_local_stack import prepare


def test_demo_config_never_overwrites_existing_env_or_credentials(tmp_path: Path) -> None:
    (tmp_path / ".env.example").write_text(
        "KNK_ENV=local-demo\nFRED_ENABLED=false\n", encoding="utf8"
    )
    original = tmp_path / ".env"
    original.write_text("FRED_ENABLED=true\n", encoding="utf8")
    path = prepare(tmp_path)
    first = path.read_bytes()
    parsed = dotenv_values(path)
    assert parsed["POSTGRES_PASSWORD"] in parsed["DATABASE_URL"]
    assert len(parsed["POSTGRES_PASSWORD"]) >= 40
    assert (
        Fernet(parsed["AUTH_SECRET"].encode()).decrypt(
            Fernet(parsed["AUTH_SECRET"].encode()).encrypt(b"roundtrip")
        )
        == b"roundtrip"
    )
    assert parsed["ORDER_EXECUTION_ENABLED"] == "false"
    assert parsed["FRED_ENABLED"] == "false"
    with pytest.raises(FileExistsError):
        prepare(tmp_path)
    assert path.read_bytes() == first
    assert original.read_text() == "FRED_ENABLED=true\n"


def test_each_workspace_has_different_credentials(tmp_path: Path) -> None:
    values = []
    for name in ("a", "b"):
        root = tmp_path / name
        root.mkdir()
        (root / ".env.example").write_text("KNK_ENV=local-demo\n")
        values.append(dotenv_values(prepare(root)))
    for key in ("POSTGRES_PASSWORD", "AUTH_SECRET", "MINIO_SECRET_KEY", "GRAFANA_ADMIN_PASSWORD"):
        assert values[0][key] != values[1][key]
