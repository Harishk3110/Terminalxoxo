"""Version-pinned position resources retain financial units and historical provenance."""

from copy import deepcopy
from datetime import date
from decimal import Decimal as D

from app import models
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

BASE = "/api/v1/portfolios/book"


def foreign_position(client: TestClient) -> dict:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "SPY",
            "quantity": "2",
            "price": "100",
            "fx_rate_to_base": "1.2",
        },
    )
    assert response.status_code == 201, response.text
    summary = client.get(BASE + "/summary?end=2026-01-07")
    assert summary.status_code == 200, summary.text
    return summary.json()


def test_position_resource_exposes_currency_units_and_exact_decomposition(
    client: TestClient,
) -> None:
    summary = foreign_position(client)
    response = client.get(BASE + "/positions/SPY", params={"run_id": summary["valuation_run_id"]})
    assert response.status_code == 200, response.text
    row = response.json()
    assert row["direction"] == "LONG"
    assert row["currency"] == "USD"
    assert row["base_currency"] == "SGD"
    assert row["portfolio_id"] == "book"
    assert row["valuation_date"] == "2026-01-07"
    assert row["calculation_version"] == "knk-nav-4.4"
    assert row["measurement_state"] == row["valuation_state"] == "AVAILABLE"
    assert D(row["cost_basis_native"]) == D(200)
    assert D(row["cost_basis_base"]) == D(240)
    assert D(row["market_value_native"]) == D(240)
    assert D(row["market_value_base_exact"]) == D(312)
    assert D(row["unrealised_price_pnl_base"]) == D(52)
    assert D(row["unrealised_fx_pnl_base"]) == D(20)
    assert D(row["unrealised_pnl"]) == D(72)
    assert D(row["nav_weight"]) == D(312) / D(summary["portfolio"]["nav"])
    assert row["sector_weight"] == row["nav_weight"]
    assert row["beta"] is None
    assert row["beta_contribution"] is None
    assert row["price_provenance"]["source"] == row["fx_provenance"]["source"] == "TEST"


def test_saved_position_is_not_repriced_when_current_observations_change(
    client: TestClient, ledger_session: Session
) -> None:
    summary = foreign_position(client)
    path = BASE + "/positions/SPY"
    params = {"run_id": summary["valuation_run_id"]}
    original = client.get(path, params=params).json()
    for row in ledger_session.scalars(
        select(models.MarketObservation).where(models.MarketObservation.instrument_id == "SPY")
    ):
        row.price = D(150)
    ledger_session.commit()
    current = client.get(path, params={"end": "2026-01-07"}).json()
    assert D(current["market_value_native"]) == D(300)
    assert current["valuation_run_id"] != summary["valuation_run_id"]
    assert client.get(path, params=params).json() == original
    assert D(original["market_value_native"]) == D(240)


def test_position_snapshot_rejects_cross_portfolio_and_conflicting_time_selectors(
    client: TestClient,
) -> None:
    summary = foreign_position(client)
    other = client.post(
        "/api/v1/portfolios",
        json={
            "code": "OTHER_BOOK",
            "name": "Other test book",
            "reference_capital": "100",
            "opening_date": "2026-01-05",
        },
    )
    assert other.status_code == 201, other.text
    run_id = summary["valuation_run_id"]
    response = client.get(
        f"/api/v1/portfolios/{other.json()['id']}/positions/SPY", params={"run_id": run_id}
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Valuation run not found in portfolio"
    assert client.get(BASE + "/positions/SPY?run_id=missing").status_code == 404
    assert client.get(BASE + "/positions/AAA", params={"run_id": run_id}).status_code == 404
    ambiguous = client.get(BASE + "/positions/SPY", params={"run_id": run_id, "end": "2026-01-07"})
    assert ambiguous.status_code == 422
    assert "not both" in ambiguous.json()["detail"]


def test_missing_current_fx_preserves_native_position_measurements(
    client: TestClient, ledger_session: Session
) -> None:
    foreign_position(client)
    ledger_session.execute(delete(models.FxObservation))
    ledger_session.commit()
    response = client.get(BASE + "/positions/SPY?end=2026-01-07")
    assert response.status_code == 200, response.text
    row = response.json()
    assert D(row["market_value_native"]) == D(240)
    assert row["market_value"] is None
    assert row["unrealised_price_pnl_base"] is None
    assert row["unrealised_fx_pnl_base"] is None
    assert row["valuation_state"] == "UNAVAILABLE"
    assert row["valuation_warnings"] == ["Position FX is unavailable"]
    assert row["nav_weight"] is None
    assert row["sector_weight"] is None
    assert row["beta_contribution"] is None


def test_legacy_position_snapshot_is_explicit_and_never_reconstructed_with_current_fields(
    client: TestClient, ledger_session: Session
) -> None:
    summary = foreign_position(client)
    payload = deepcopy(summary)
    for row in payload["positions"]:
        for name in (
            "direction",
            "cost_basis_native",
            "market_value_native",
            "market_value_base_exact",
            "unrealised_pnl_native",
            "unrealised_price_pnl_base",
            "unrealised_fx_pnl_base",
            "nav_weight",
            "sector_weight",
            "beta_contribution",
            "valuation_state",
            "valuation_warnings",
            "unrealised_decomposition_method",
            "daily_pnl_details",
        ):
            row.pop(name, None)
    payload.pop("lots")
    payload.pop("lot_matches")
    payload["portfolio"].pop("accounting_policy")
    payload["calculation_version"] = "knk-nav-3.0"
    payload["valuation_run_id"] = "legacy-run"
    ledger_session.add(
        models.PortfolioValuationRun(
            id="legacy-run",
            portfolio_id="book",
            fingerprint="legacy-position",
            valuation_date=date.fromisoformat(summary["curve"][-1]["date"]),
            status="SUCCEEDED",
            nav=D(summary["portfolio"]["nav"]),
            payload=payload,
        )
    )
    ledger_session.commit()
    response = client.get(BASE + "/positions/SPY?run_id=legacy-run")
    assert response.status_code == 200, response.text
    row = response.json()
    assert row["measurement_state"] == "LEGACY_SNAPSHOT"
    assert "market_value_native" not in row
    assert "daily_pnl_details" not in row
    assert row["lots"] == row["matches"] == []
    assert row["accounting_policy"] is None
    assert row["calculation_version"] == "knk-nav-3.0"
    assert row["market_value"] == summary["positions"][0]["market_value"]
