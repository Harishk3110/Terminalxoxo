"""Verify reports in a newly created PostgreSQL database, never the active book.

Run inside the API image: python scripts/report_smoke.py --isolated-postgres.
The uniquely named verification database and private objects are retained as evidence.
"""

import argparse
import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--isolated-postgres", action="store_true", required=True)
    parser.parse_args()
    url = make_url(os.environ["DATABASE_URL"])
    if url.get_backend_name() != "postgresql":
        raise SystemExit(
            "This smoke requires PostgreSQL; the active database is never restored over"
        )
    name = (
        "knk_report_verify_" + datetime.now(UTC).strftime("%Y%m%d_%H%M%S_") + secrets.token_hex(3)
    )
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    admin.dispose()
    os.environ["DATABASE_URL"] = url.set(database=name).render_as_string(hide_password=False)
    os.environ["KNK_ENV"] = "local-demo"
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True)
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from app.main import app
    from fastapi.testclient import TestClient

    with socket.socket() as port_socket:
        port_socket.bind(("127.0.0.1", 0))
        port = port_socket.getsockname()[1]
    worker = None
    results = []
    try:
        with TestClient(app) as client:
            password = secrets.token_urlsafe(32)
            credentials = {"email": name + "@example.test", "password": password}
            assert client.post("/api/v1/auth/setup", json=credentials).status_code == 200
            assert client.post("/api/v1/auth/login", json=credentials).status_code == 200
            for format in ("xlsx", "pptx", "pdf"):
                response = client.post(
                    "/api/v1/report-jobs",
                    json={"kind": "portfolio", "format": format, "as_of": "2026-09-04"},
                )
                assert response.status_code == 202, response.text
                results.append(response.json())
            worker = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app.report_engine:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=root,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deadline = time.monotonic() + 120
            for result in results:
                path = f"/api/v1/report-jobs/{result['id']}"
                while True:
                    status = client.get(path).json()
                    if status["status"] == "FAILED":
                        raise RuntimeError("Report failed: " + str(status["error_category"]))
                    if status["status"] == "SUCCEEDED":
                        break
                    if time.monotonic() > deadline or worker.poll() is not None:
                        raise RuntimeError("Report worker failed or timed out")
                    time.sleep(0.5)
                downloaded = client.get(status["download_url"])
                assert downloaded.status_code == 200
                assert hashlib.sha256(downloaded.content).hexdigest() == status["content_hash"]
                result.update(status)
            worker.terminate()
            worker.wait(timeout=15)
            worker = None
            for result in results:
                response = client.get(result["download_url"])
                assert response.status_code == 200
                assert hashlib.sha256(response.content).hexdigest() == result["content_hash"]
            client.cookies.clear()
            assert all(client.get(row["download_url"]).status_code == 401 for row in results)
        print(
            json.dumps(
                {
                    "verification_database": name,
                    "active_database_untouched": True,
                    "anonymous_download": "REJECTED",
                    "worker_exit_persistence": "PASS",
                    "reports": [
                        {
                            key: row[key]
                            for key in (
                                "id",
                                "format",
                                "snapshot_hash",
                                "content_hash",
                                "size_bytes",
                            )
                        }
                        for row in results
                    ],
                }
            )
        )
    finally:
        if worker is not None and worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=15)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)


if __name__ == "__main__":
    main()
