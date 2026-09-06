from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_environment_badges_are_explicit():
    response = client.get("/api/v1/environment")
    assert response.status_code == 200
    payload = response.json()
    assert "DEMO DATA" in payload["badges"]
    assert payload["paper_only"] is True


def test_public_content_route_is_removed():
    response = client.get("/api/v1/public/content")
    assert response.status_code == 404
    text = response.text.lower()
    assert "portfolio_transactions" not in text
    assert "broker_password" not in text
    assert "provider_secret" not in text


def test_portfolio_is_database_backed_and_demo_labelled():
    response = client.get("/api/v1/portfolios/default")
    assert response.status_code == 200
    payload = response.json()
    assert payload["portfolio"]["base_currency"] == "SGD"
    assert payload["portfolio"]["reference_capital"] == "100000.00000000"
    assert len(payload["positions"]) >= 3
    assert all(row["quality"] == "DEMO DATA" for row in payload["positions"])


def test_macro_dashboard_returns_persisted_series():
    response = client.get("/api/v1/macro/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["items"]) >= 10
    fedfunds = [item for item in payload["items"] if item["series_id"] == "FEDFUNDS"][0]
    assert fedfunds["latest_value"] is not None
    assert fedfunds["quality"] == "DEMO DATA"


def test_add_manual_transaction_recalculates_portfolio():
    before = client.get("/api/v1/portfolios/default").json()["portfolio"]["nav"]
    response = client.post(
        "/api/v1/portfolios/default/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-09-05",
            "symbol": "AAPL",
            "quantity": "1",
            "price": "200",
            "currency": "USD",
            "fx_rate_to_base": "1.33",
            "fee": "1.00",
            "notes": "test transaction",
        },
    )
    assert response.status_code == 200
    after = client.get("/api/v1/portfolios/default").json()["portfolio"]["nav"]
    assert after != before


def test_fred_status_truthful_without_credentials():
    response = client.get("/api/v1/providers/fred/status")
    assert response.status_code == 200
    payload = response.json()
    assert payload["configured"] is False
    assert payload["connection_state"] in {"NOT_CONFIGURED", "FAILED"}
