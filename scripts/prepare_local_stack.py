"""Create a separate local-demo Compose environment without overwriting secrets."""

import argparse
import json
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import dotenv_values


def prepare(root: Path) -> Path:
    root = root.resolve(strict=True)
    target = root / ".env.compose.local"
    values = {key: value or "" for key, value in dotenv_values(root / ".env.example").items()}
    password = secrets.token_urlsafe(32)
    values.update(
        {
            "COMPOSE_PROJECT_NAME": "knk-final-local",
            "KNK_COMPOSE_ENV_FILE": ".env.compose.local",
            "KNK_ENV": "local-demo",
            "POSTGRES_PASSWORD": password,
            "DATABASE_URL": f"postgresql+psycopg://knk:{password}@postgres:5432/knk_terminal",
            "MINIO_ACCESS_KEY": "knk" + secrets.token_hex(8),
            "MINIO_SECRET_KEY": secrets.token_urlsafe(32),
            "GRAFANA_ADMIN_PASSWORD": secrets.token_urlsafe(32),
            "AUTH_SECRET": Fernet.generate_key().decode("ascii"),
            "PAPER_ONLY": "true",
            "ORDER_EXECUTION_ENABLED": "false",
            "FRED_ENABLED": "false",
            "SEC_ENABLED": "false",
            "OPENFIGI_ENABLED": "false",
            "MARKET_DATA_ENABLED": "false",
            "OPTIONS_DATA_ENABLED": "false",
        }
    )
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(
            "# Private generated local-demo configuration. Preserve for volume recovery.\n"
        )
        for key, value in values.items():
            stream.write(f"{key}={json.dumps(value)}\n")
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        target = prepare(args.root)
    except FileExistsError:
        print("Existing .env.compose.local preserved; no credentials rotated.")
        return 0
    print(f"Created private {target.name}; no existing environment or database modified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
