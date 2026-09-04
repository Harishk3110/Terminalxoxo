from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_environment_badges_are_explicit():
    response = client.get("/api/environment")
    assert response.status_code == 200
    payload = response.json()
    assert "DEMO DATA" in payload["badges"]
    assert payload["paper_only"] is True


def test_public_content_does_not_return_private_portfolio_data():
    response = client.get("/api/public/content")
    assert response.status_code == 200
    text = response.text.lower()
    assert "positions" not in text
    assert "broker" not in text
    assert "private" not in text


def test_portfolio_trace_is_demo_labelled():
    response = client.get("/api/portfolio")
    assert response.status_code == 200
    payload = response.json()
    assert payload["trace"]["quality"] == "DEMO DATA"
    assert payload["base_currency"] == "SGD"
