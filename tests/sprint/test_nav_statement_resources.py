"""Version-pinned NAV statements preserve full liability presentation and missing states."""

from copy import deepcopy
from datetime import date
from decimal import Decimal as D

from app import models
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

BASE = "/api/v1/portfolios/book"


def buy(client: TestClient, **fields) -> None:
    response = client.post(
        BASE + "/transactions",
        json={
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "settle_date": "2026-01-08",
            "symbol": "SPY",
            "quantity": "2",
            "price": "100",
            "fx_rate_to_base": "1.2",
            **fields,
        },
    )
    assert response.status_code == 201, response.text


def statement(client: TestClient, day="2026-01-09") -> dict:
    response = client.get(BASE + "/nav", params={"end": day})
    assert response.status_code == 200, response.text
    return response.json()


def test_currency_overdraft_is_preserved_in_gross_assets_and_liabilities_after_settlement(
    client: TestClient,
) -> None:
    buy(client)
    before = statement(client, "2026-01-07")
    after = statement(client)
    for data in (before, after):
        items = data["balance_sheet"]["items"]
        assert D(items["gross_asset_value"]) == D(10312)
        assert D(items["liabilities"]) == D(260)
        assert D(items["nav"]) == D(10052)
        assert D(items["cash_assets"]) == D(10000)
        assert D(data["balance_sheet"]["difference"]) == 0
        assert data["balance_sheet"]["reconciliation_state"] == "BALANCED"
        assert data["balance_sheet"]["state"] == data["state"] == "AVAILABLE"
        assert data["calculation_version"] == "knk-nav-4.7"
    assert D(before["balance_sheet"]["items"]["payables"]) == D(260)
    assert D(before["balance_sheet"]["items"]["cash_overdrafts"]) == 0
    assert D(after["balance_sheet"]["items"]["payables"]) == 0
    assert D(after["balance_sheet"]["items"]["cash_overdrafts"]) == D(260)
    assert D(after["portfolio"]["gross_asset_value"]) == D(10312)
    assert D(after["portfolio"]["liabilities"]) == D(260)


def test_short_proceeds_remain_cash_assets_and_short_mark_is_a_separate_liability(
    client: TestClient,
) -> None:
    buy(client, transaction_type="SHORT", symbol="AAA", fx_rate_to_base="1")
    data = statement(client)
    items = data["balance_sheet"]["items"]
    assert D(items["cash_assets"]) == D(10200)
    assert D(items["long_market_value"]) == 0
    assert D(items["short_liabilities"]) == D(240)
    assert D(items["market_value"]) == D(-240)
    assert D(items["liabilities"]) == D(240)
    assert D(items["nav"]) == D(9960)
    assert data["reconciliation"]["state"] == "BALANCED"


def test_recorded_fee_balance_is_not_counted_as_short_liability_or_paid_cash(
    client: TestClient,
) -> None:
    buy(client, transaction_type="SHORT", symbol="AAA", fx_rate_to_base="1")
    response = client.post(
        BASE + "/balances",
        json={
            "effective_date": "2026-01-07",
            "bucket": "accrued_fees",
            "currency": "SGD",
            "amount": "12.34567891",
            "reason": "Recognized management charge",
        },
    )
    assert response.status_code == 201, response.text
    data = statement(client)
    items = data["balance_sheet"]["items"]
    assert D(items["accrued_fees"]) == D("12.34567891")
    assert D(items["liabilities"]) == D("252.34567891")
    assert D(items["cash"]) == D(10200)
    assert D(items["nav"]) == D("9947.65432109")
    assert D(data["portfolio"]["nav"]) == D("9947.65")
    assert D(data["balance_sheet"]["difference"]) == 0


def test_unknown_short_price_does_not_show_zero_liabilities_or_a_complete_balance_sheet(
    client: TestClient,
    ledger_session: Session,
) -> None:
    buy(client, transaction_type="SHORT", symbol="AAA", fx_rate_to_base="1")
    ledger_session.execute(
        delete(models.MarketObservation).where(models.MarketObservation.instrument_id == "AAA")
    )
    ledger_session.commit()
    data = statement(client)
    assert data["state"] == "INCOMPLETE"
    assert all(value is None for value in data["balance_sheet"]["items"].values())
    assert data["balance_sheet"]["difference"] is None
    assert data["balance_sheet"]["reconciliation_state"] == "INCOMPLETE"
    assert data["balance_sheet"]["warnings"] == ["AAA: missing price"]
    assert data["portfolio"]["liabilities"] is None
    assert data["portfolio"]["gross_asset_value"] is None
    assert D(data["portfolio"]["cash"]) == D(10200)


def test_saved_nav_statement_does_not_reprice_when_current_marks_change(
    client: TestClient,
    ledger_session: Session,
) -> None:
    buy(client)
    original = statement(client)
    for row in ledger_session.scalars(select(models.FxObservation)):
        row.rate = D(2)
    ledger_session.commit()
    saved = client.get(BASE + "/nav", params={"run_id": original["valuation_run_id"]})
    assert saved.status_code == 200
    assert saved.json() == original
    assert statement(client)["portfolio"]["nav"] != original["portfolio"]["nav"]


def test_nav_run_selection_enforces_portfolio_scope_and_exclusive_date_parameters(
    client: TestClient,
) -> None:
    original = statement(client)
    run = original["valuation_run_id"]
    other = client.post(
        "/api/v1/portfolios",
        json={
            "code": "SECOND_NAV",
            "name": "Second NAV book",
            "reference_capital": "100",
            "opening_date": "2026-01-05",
        },
    )
    assert other.status_code == 201
    assert (
        client.get(
            f"/api/v1/portfolios/{other.json()['id']}/nav", params={"run_id": run}
        ).status_code
        == 404
    )
    assert client.get(BASE + "/nav?run_id=missing").status_code == 404
    assert client.get(BASE + "/nav", params={"run_id": run, "end": "2026-01-09"}).status_code == 422


def test_legacy_nav_does_not_reconstruct_a_statement_from_partial_aggregate_fields(
    client: TestClient,
    ledger_session: Session,
) -> None:
    current = client.get(BASE + "/summary?end=2026-01-09").json()
    payload = deepcopy(current)
    payload.pop("balance_sheet")
    payload["valuation_run_id"] = "legacy-nav"
    payload["calculation_version"] = "knk-nav-4.5"
    ledger_session.add(
        models.PortfolioValuationRun(
            id="legacy-nav",
            portfolio_id="book",
            fingerprint="legacy-nav",
            valuation_date=date(2026, 1, 9),
            nav=D(10000),
            status="SUCCEEDED",
            payload=payload,
        )
    )
    ledger_session.commit()
    result = client.get(BASE + "/nav?run_id=legacy-nav").json()
    assert result["state"] == "LEGACY_SNAPSHOT"
    assert result["balance_sheet"] is None
    assert result["portfolio"] == payload["portfolio"]
    assert result["calculation_version"] == "knk-nav-4.5"
