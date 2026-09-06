import csv
import io

import pytest
from app import models
from app.config import get_settings
from app.database import get_session
from app.pine_api import router
from app.pine_research import PineSettings, compare_export, generate
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select


def export_file(signal="1", periods=80):
    import pandas as pd

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["time", "close", "KNK_SIGNAL"])
    for i, timestamp in enumerate(pd.date_range("2025-01-01", periods=periods, tz="UTC")):
        writer.writerow([timestamp.isoformat(), 100 + i, signal])
    return output.getvalue().encode()


@pytest.mark.parametrize("strategy", ["SMA", "RSI", "MACD", "BREAKOUT"])
def test_template_constants_and_honest_compatibility(strategy):
    result = generate(PineSettings(strategy=strategy, trailing_ticks=10))
    assert result["source"].startswith("//@version=6")
    assert "commission_value=input" not in result["source"]
    assert "alert(" in result["source"] and "trail_points=" in result["source"]
    assert result["compilation"] == "UNVERIFIED"
    assert result["comparison"] == "NOT_COMPARED"
    assert len(result["source_hash"]) == 64


@pytest.mark.parametrize(
    "payload",
    [
        {"fast": 51},
        {"commission_pct": float("nan")},
        {"stop_pct": 5, "trailing_ticks": 2},
        {"session": '0900-1700"\n'},
        {"session": "2900-1700"},
        {"end": "2010-01-01"},
    ],
)
def test_invalid_template_inputs(payload):
    with pytest.raises(ValueError):
        PineSettings(**payload)


def test_comparison_reports_only_observed_post_warmup():
    result = compare_export(export_file(), PineSettings())
    assert result["compared"] == 31 and result["warmup_excluded"] == 49
    assert result["match_rate"] == 1 and result["mismatch_count"] == 0
    result = compare_export(export_file("-1"), PineSettings())
    assert result["mismatch_count"] == 31 and result["match_rate"] == 0
    assert result["state"] == "MISMATCHES"


@pytest.mark.parametrize(
    "raw",
    [
        export_file("nan"),
        export_file("2"),
        export_file(""),
        export_file(periods=10),
        b"time,close,close,KNK_SIGNAL\n",
        b"date,price,signal\n",
    ],
)
def test_invalid_or_empty_comparison(raw):
    with pytest.raises(ValueError):
        compare_export(raw, PineSettings())


def test_saved_template_comparison_auth_and_ledger_unchanged(
    ledger_session, session_token, monkeypatch, tmp_path
):
    monkeypatch.setattr(get_settings(), "object_storage_local_dir", str(tmp_path))
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    before = ledger_session.scalar(select(func.count()).select_from(models.PortfolioTransaction))
    with TestClient(app) as client:
        assert client.post("/api/v1/pine/generate", json={}).status_code == 403
        client.cookies.set("knk_session", session_token)
        created = client.post("/api/v1/pine/generate", json={})
        assert created.status_code == 201, created.text
        template = created.json()
        result = client.post(
            f"/api/v1/pine/{template['id']}/compare",
            files={"file": ("chart.csv", export_file(), "text/csv")},
        )
        assert result.status_code == 201, result.text
        saved = ledger_session.get(models.AnalysisRun, result.json()["id"])
        assert saved.parameters["template_hash"] == template["source_hash"]
        assert saved.kind == "pine_compare"
        assert (
            ledger_session.scalar(select(func.count()).select_from(models.PortfolioTransaction))
            == before
        )
