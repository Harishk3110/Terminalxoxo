from pathlib import Path
from runpy import run_path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]


def client_for(path: str) -> TestClient:
    app: object = run_path(str(ROOT / path))["app"]
    assert isinstance(app, FastAPI)
    return TestClient(app)


def test_legacy_broker_does_not_claim_connection_pairing_or_account_data() -> None:
    with client_for("services/broker-agent/agent/main.py") as client:
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 503
        assert client.get("/status").json() == {
            "state": "DISABLED",
            "read_only": True,
            "paired": False,
            "source": "UNAVAILABLE",
        }
        pair = client.post("/pair", json={"device_name": "fixture", "one_time_code": "unused"})
        assert pair.status_code == 410
        assert set(pair.json()) == {"detail"}
        snapshot = client.get("/snapshots/account")
        assert snapshot.status_code == 503
        assert set(snapshot.json()) == {"detail"}
        metrics = client.get("/metrics")
        assert metrics.headers["content-type"].startswith("text/plain")
        assert "knk_broker_legacy_disabled 1" in metrics.text
        assert "heartbeat" not in metrics.text


@pytest.mark.parametrize(
    "method,path", [("POST", "/reports"), ("GET", "/reports/fixture/download")]
)
def test_legacy_report_renderer_never_bypasses_private_queue(method: str, path: str) -> None:
    with client_for("services/report-engine/app/main.py") as client:
        assert client.get("/health/live").json()["rendering"] == "DISABLED"
        assert client.get("/health/ready").status_code == 503
        assert client.request(method, path).status_code == 403
