"""Opt-in migrations and real process restarts in newly allocated databases only."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from dotenv import dotenv_values
from pydantic import BaseModel, JsonValue, TypeAdapter
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url

from infrastructure.scripts.managed_postgres import Postgres
from scripts.release_candidate import ROOT, stop_process_tree
from scripts.release_checks import local_configuration

JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


@dataclass(frozen=True)
class IsolatedDatabase:
    name: str
    environment: dict[str, str] = field(repr=False)


@pytest.fixture
def isolated_postgres(tmp_path: Path) -> IsolatedDatabase:
    file = os.environ.get("KNK_MANAGED_BACKUP_TEST_ENV")
    if not file:
        pytest.skip("Local PostgreSQL lifecycle test requires KNK_MANAGED_BACKUP_TEST_ENV")
    local_configuration(Path(file))
    values = dotenv_values(file)
    source = make_url(values["DATABASE_URL"] or "").set(host="127.0.0.1")
    name = "knk_restore_" + uuid4().hex
    Postgres(source.render_as_string(hide_password=False)).create_isolated_database(name)
    environment = {
        **os.environ,
        "DATABASE_URL": source.set(database=name).render_as_string(hide_password=False),
        "KNK_ENV": "local-demo",
        "OBJECT_STORAGE_LOCAL_DIR": str(tmp_path / "objects"),
        "MINIO_ENDPOINT": "",
        "MINIO_ACCESS_KEY": "",
        "MINIO_SECRET_KEY": "",
        "KNK_AUTH_KEY_FILE": str(tmp_path / "private-auth.key"),
        "AUTH_SECRET": secrets.token_urlsafe(48),
        "FRED_ENABLED": "false",
        "SEC_ENABLED": "false",
        "OPENFIGI_ENABLED": "false",
        "MARKET_DATA_ENABLED": "false",
        "OPTIONS_DATA_ENABLED": "false",
    }
    (tmp_path / "database.json").write_text(
        json.dumps({"database": name, "active_database_untouched": True}), encoding="utf-8"
    )
    return IsolatedDatabase(name, environment)


def migrate(database: IsolatedDatabase, folder: Path, direction: str, revision: str) -> None:
    assert direction in {"upgrade", "downgrade"}
    with (folder / f"migration-{direction}-{revision.replace('-', 'minus')}.log").open(
        "ab"
    ) as stream:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", direction, revision],
            cwd=ROOT,
            env=database.environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
    assert result.returncode == 0, "Isolated migration failed; inspect the local migration log"


def test_postgres_latest_downgrade_upgrade_retains_existing_book(
    isolated_postgres: IsolatedDatabase,
    tmp_path: Path,
) -> None:
    migrate(isolated_postgres, tmp_path, "upgrade", "head")
    engine = create_engine(isolated_postgres.environment["DATABASE_URL"])
    try:
        before = {
            table: {column["name"] for column in inspect(engine).get_columns(table)}
            for table in inspect(engine).get_table_names()
        }
        with engine.begin() as connection:
            head = connection.scalar(text("SELECT version_num FROM alembic_version"))
            connection.execute(
                text(
                    "INSERT INTO portfolios (id, name, base_currency, reference_capital, is_default, created_at, updated_at) "
                    "VALUES ('retained', 'Isolated migration fixture', 'SGD', 100000.12345678, false, '2026-01-01', '2026-01-01')"
                )
            )
        migrate(isolated_postgres, tmp_path, "downgrade", "-1")
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) != head
        migrate(isolated_postgres, tmp_path, "upgrade", "head")
        after = {
            table: {column["name"] for column in inspect(engine).get_columns(table)}
            for table in inspect(engine).get_table_names()
        }
        assert after == before
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == head
            assert connection.scalar(
                text("SELECT reference_capital FROM portfolios WHERE id='retained'")
            ) == Decimal("100000.12345678")
            assert connection.scalar(text("SELECT COUNT(*) FROM portfolios")) == 1
    finally:
        engine.dispose()


@contextmanager
def serve(
    database: IsolatedDatabase, folder: Path, label: str, application: str
) -> Iterator[tuple[httpx.Client, int]]:
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with (folder / (label + ".log")).open("xb") as stream:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                application,
                "--app-dir",
                "services/api",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            cwd=ROOT,
            env=database.environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            start_new_session=os.name != "nt",
        )
        try:
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
                deadline = time.monotonic() + 120
                while True:
                    assert process.poll() is None, (
                        f"Owned {label} process exited; inspect its local log"
                    )
                    try:
                        if client.get("/health/live").status_code == 200:
                            break
                    except httpx.TransportError:
                        pass
                    assert time.monotonic() < deadline, f"Owned {label} process did not become live"
                    time.sleep(0.2)
                yield client, process.pid
        finally:
            if process.poll() is None:
                stop_process_tree(process, stream)


def response_json(response: httpx.Response, expected: int = 200) -> dict[str, JsonValue]:
    assert response.status_code == expected, f"Unexpected API status {response.status_code}"
    return JSON_OBJECT.validate_json(response.content)


class PortfolioValue(BaseModel):
    nav: Decimal
    cash: Decimal
    market_value: Decimal
    base_currency: str
    execution_mode: str


class PositionValue(BaseModel):
    quantity: Decimal
    realised_pnl: Decimal


class Summary(BaseModel):
    portfolio: PortfolioValue
    positions: list[PositionValue]
    valuation_run_id: str


def test_api_and_worker_restart_preserve_ledger_nav_and_private_report(
    isolated_postgres: IsolatedDatabase,
    tmp_path: Path,
) -> None:
    migrate(isolated_postgres, tmp_path, "upgrade", "head")
    credentials = {
        "email": "restart-" + uuid4().hex + "@example.test",
        "password": secrets.token_urlsafe(32),
    }
    with serve(isolated_postgres, tmp_path, "api-before", "app.main:app") as (client, api_before):
        response_json(client.post("/api/v1/auth/setup", json=credentials))
        response_json(client.post("/api/v1/auth/login", json=credentials))
        created = response_json(
            client.post(
                "/api/v1/portfolios",
                json={
                    "code": "RESTART_FIXTURE",
                    "name": "Isolated restart fixture",
                    "base_currency": "SGD",
                    "reference_capital": "100000",
                    "opening_date": "2026-09-01",
                    "method": "FIFO",
                    "benchmark": "SPY",
                },
            ),
            201,
        )
        identifier = created["id"]
        assert isinstance(identifier, str)
        route = f"/api/v1/portfolios/{identifier}"
        for payload in (
            {
                "transaction_type": "BUY",
                "trade_date": "2026-09-01",
                "symbol": "D05",
                "quantity": "10",
                "price": "30",
            },
            {
                "transaction_type": "SELL",
                "trade_date": "2026-09-02",
                "symbol": "D05",
                "quantity": "4",
                "price": "35",
            },
            {
                "transaction_type": "DIVIDEND",
                "trade_date": "2026-09-03",
                "symbol": "D05",
                "amount": "12",
            },
        ):
            response_json(client.post(route + "/transactions", json=payload), 201)
        before = response_json(client.get(route + "/summary?end=2026-09-04"))
        summary = Summary.model_validate(before)
        assert summary.portfolio.cash == Decimal("99852")
        assert summary.portfolio.nav == summary.portfolio.cash + summary.portfolio.market_value
        assert (
            summary.portfolio.base_currency == "SGD"
            and summary.portfolio.execution_mode == "MANUAL"
        )
        assert len(summary.positions) == 1 and summary.positions[0].quantity == 6
        assert summary.positions[0].realised_pnl == 20
        transactions = response_json(client.get(route + "/transactions"))
        job = response_json(
            client.post(
                "/api/v1/report-jobs",
                json={
                    "kind": "portfolio",
                    "format": "xlsx",
                    "portfolio": identifier,
                    "valuation_run_id": summary.valuation_run_id,
                },
            ),
            202,
        )
        assert isinstance(job["id"], str)
        job_path = "/api/v1/report-jobs/" + job["id"]
        with serve(isolated_postgres, tmp_path, "worker-before", "app.report_engine:app") as (
            _,
            worker_before,
        ):
            deadline = time.monotonic() + 90
            while True:
                job = response_json(client.get(job_path))
                assert job["status"] != "FAILED", "Isolated report job failed"
                if job["status"] == "SUCCEEDED":
                    break
                assert time.monotonic() < deadline, "Isolated report job timed out"
                time.sleep(0.25)
            assert isinstance(job["download_url"], str)
            artifact = client.get(job["download_url"])
            assert artifact.status_code == 200
            artifact_hash = hashlib.sha256(artifact.content).hexdigest()
            assert artifact_hash == job["content_hash"]
        cookies = dict(client.cookies)
    # Both owned processes have exited. New processes must use persisted state.
    with serve(isolated_postgres, tmp_path, "api-after", "app.main:app") as (client, api_after):
        assert api_before != api_after
        assert client.get(route + "/transactions").status_code == 401
        client.cookies.update(cookies)
        assert response_json(client.get(route + "/transactions")) == transactions
        assert response_json(client.get(route + "/summary?end=2026-09-04")) == before
        with serve(isolated_postgres, tmp_path, "worker-after", "app.report_engine:app") as (
            _,
            worker_after,
        ):
            assert worker_before != worker_after
            assert response_json(client.get(job_path)) == job
            assert isinstance(job["download_url"], str)
            artifact = client.get(job["download_url"])
            assert (
                artifact.status_code == 200
                and hashlib.sha256(artifact.content).hexdigest() == artifact_hash
            )
            listed = response_json(client.get("/api/v1/report-jobs"))["items"]
            assert isinstance(listed, list) and len(listed) == 1
        client.cookies.clear()
        assert client.get(job["download_url"]).status_code == 401
    (tmp_path / "restart-evidence.json").write_text(
        json.dumps(
            {
                "database": isolated_postgres.name,
                "active_database_untouched": True,
                "api_processes": [api_before, api_after],
                "worker_processes": [worker_before, worker_after],
                "valuation_run_id": summary.valuation_run_id,
                "report_id": job["id"],
                "artifact_sha256": artifact_hash,
                "ledger_and_nav_unchanged": True,
                "session_survived_restart": True,
                "anonymous_download": "REJECTED",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
