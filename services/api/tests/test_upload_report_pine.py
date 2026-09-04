from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_dataset_upload_infers_csv_schema():
    response = client.post(
        "/api/v1/uploads",
        files={"file": ("prices.csv", b"date,ticker,close\n2026-09-05,AAPL,231.42\n", "text/csv")},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["row_count"] == 1
    assert [column["name"] for column in payload["columns"]] == ["date", "ticker", "close"]


def test_report_generation_creates_workbook_object():
    response = client.post("/api/v1/reports/portfolio-xlsx")
    assert response.status_code == 200
    payload = response.json()
    assert payload["object_key"].endswith(".xlsx")
    assert payload["size_bytes"] > 1000


def test_pine_export_contains_strategy_rules_without_execution_claims():
    response = client.get("/api/v1/pine/export")
    assert response.status_code == 200
    payload = response.json()
    assert payload["compatibility"] == "SUPPORTED"
    assert "strategy.entry" in payload["source"]
    assert "broker" not in payload["source"].lower()
