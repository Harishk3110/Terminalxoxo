"""Historical exposure resources include cash FX and net outstanding balances."""

from copy import deepcopy
from datetime import date
from decimal import Decimal as D

import pytest
from app import models
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

BASE = "/api/v1/portfolios/book"


def trade(client: TestClient, **fields) -> dict:
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
    return response.json()


def balance(client: TestClient, **fields) -> None:
    response = client.post(
        BASE + "/balances",
        json={
            "effective_date": "2026-01-06",
            "bucket": "accrued_income",
            "currency": "USD",
            "amount": "50",
            "reason": "Exposure resource test adjustment",
            **fields,
        },
    )
    assert response.status_code == 201, response.text


def exposures(client: TestClient, **params) -> dict:
    response = client.get(BASE + "/exposures", params={"end": "2026-01-07", **params})
    assert response.status_code == 200, response.text
    return response.json()


def test_economic_cash_exposure_includes_trade_payable_exactly_once(client: TestClient) -> None:
    trade(client)
    data = exposures(client)
    currencies = {r["name"]: r for r in data["groups"]["currency"]}
    assert D(currencies["USD"]["long_value"]) == D(312)
    assert D(currencies["USD"]["cash_value"]) == D(-260)
    assert D(currencies["USD"]["balance_value"]) == 0
    assert D(currencies["USD"]["net_value"]) == D(52)
    assert sum(D(r["net_value"]) for r in currencies.values()) == D(data["nav"]) == D(10052)
    assert data["balances"] == []
    assert data["state"] == "AVAILABLE"
    assert data["base_currency"] == "SGD"
    assert data["calculation_version"] == "knk-nav-4.5"
    after = exposures(client, end="2026-01-09")
    assert after["groups"] == data["groups"]


def test_unpriced_position_group_is_not_silently_omitted(
    client: TestClient,
    ledger_session: Session,
) -> None:
    trade(client)
    ledger_session.execute(
        delete(models.MarketObservation).where(models.MarketObservation.instrument_id == "SPY")
    )
    ledger_session.commit()
    data = exposures(client)
    row = next(r for r in data["groups"]["currency"] if r["name"] == "USD")
    assert row["net_value"] is row["weight"] is None
    assert D(row["known_value"]) == D(-260)
    assert D(row["cash_value"]) == D(-260)
    assert row["long_value"] is row["short_value"] is None
    assert row["missing_count"] == 1
    assert data["nav"] is None
    assert data["state"] == "INCOMPLETE"
    assert data["freshness"]["price_coverage_pct"] == 0


def test_missing_cash_fx_and_position_fx_are_visible_as_two_unknown_components(
    client: TestClient,
    ledger_session: Session,
) -> None:
    trade(client)
    ledger_session.execute(delete(models.FxObservation))
    ledger_session.commit()
    data = exposures(client)
    row = next(r for r in data["groups"]["currency"] if r["name"] == "USD")
    assert row["missing_count"] == 2
    assert row["cash_value"] is None
    assert data["freshness"]["unavailable_items"] == 2
    assert data["freshness"]["cash_fx_coverage_pct"] == 50
    assert data["freshness"]["stale_nav_pct"] is None
    assert data["quality"] == "UNAVAILABLE"


def test_stale_cash_fx_is_counted_without_any_open_positions(client: TestClient) -> None:
    trade(
        client,
        transaction_type="DEPOSIT",
        symbol=None,
        quantity="0",
        price="0",
        currency="USD",
        amount="100",
        settle_date="2026-01-06",
    )
    data = exposures(client, end="2026-01-20")
    assert data["groups"]["sector"] == []
    assert data["freshness"]["stale_market_value"] == "0.00"
    assert D(data["freshness"]["stale_cash_value"]) == D(130)
    assert D(data["freshness"]["stale_total_value"]) == D(130)
    assert D(data["freshness"]["stale_nav_pct"]) == D(130) / D(10130)
    assert data["freshness"]["stale_items"] == 1
    assert data["quality"] == "CALCULATED WITH STALE DATA"


def test_price_and_fx_staleness_count_a_position_once_but_cash_separately(
    client: TestClient,
) -> None:
    trade(client)
    data = exposures(client, end="2026-01-20")
    fresh = data["freshness"]
    assert D(fresh["stale_market_value"]) == D(312)
    assert D(fresh["stale_cash_value"]) == D(260)
    assert D(fresh["stale_total_value"]) == D(572)
    assert fresh["stale_items"] == 2
    assert D(fresh["stale_nav_pct"]) == D(572) / D(10052)


@pytest.mark.parametrize(
    "bucket,sign,asset_class",
    [
        ("accrued_income", 1, "Accrual"),
        ("receivables", 1, "Accrual"),
        ("payables", -1, "Liability"),
        ("accrued_fees", -1, "Liability"),
        ("other_liabilities", -1, "Liability"),
    ],
)
def test_balance_reversals_mark_net_outstanding_bucket_not_gross_history(
    client: TestClient,
    bucket: str,
    sign: int,
    asset_class: str,
) -> None:
    balance(client, bucket=bucket)
    balance(client, bucket=bucket, amount="-20", effective_date="2026-01-07")
    data = exposures(client, end="2026-01-20")
    assert len(data["balances"]) == 1
    item = data["balances"][0]
    assert D(item["amount"]) == D(30)
    assert D(item["base_value"]) == sign * D(39)
    assert item["fx_provenance"]["stale"] is True
    assert D(data["freshness"]["stale_balance_value"]) == D(39)
    row = next(r for r in data["groups"]["asset_class"] if r["name"] == asset_class)
    assert D(row["balance_value"]) == sign * D(39)
    assert sum(D(r["net_value"]) for r in data["groups"]["currency"]) == D(data["nav"])


def test_fully_reversed_foreign_balance_needs_no_mark_at_current_date(
    client: TestClient,
    ledger_session: Session,
) -> None:
    balance(client)
    balance(client, amount="-50", effective_date="2026-01-07")
    ledger_session.execute(delete(models.FxObservation))
    ledger_session.commit()
    data = exposures(client)
    assert D(data["nav"]) == D(10000)
    assert data["balances"] == []
    assert data["freshness"]["unavailable_items"] == 0
    assert data["state"] == "AVAILABLE"


def test_missing_outstanding_balance_fx_retains_liability_group(
    client: TestClient,
    ledger_session: Session,
) -> None:
    balance(client, bucket="other_liabilities")
    ledger_session.execute(delete(models.FxObservation))
    ledger_session.commit()
    data = exposures(client)
    row = next(r for r in data["groups"]["asset_class"] if r["name"] == "Liability")
    assert row["balance_value"] is row["net_value"] is None
    assert row["missing_count"] == 1
    assert data["freshness"]["unavailable_items"] == 1
    assert data["nav"] is None


def test_base_cash_only_book_is_calculated_not_demo_data(client: TestClient) -> None:
    data = exposures(client)
    assert data["quality"] == "CALCULATED"
    assert data["groups"]["country"] == []
    cash = data["groups"]["asset_class"][0]
    assert cash["name"] == "Cash"
    assert D(cash["weight"]) == 1
    summary = client.get(BASE + "/summary?end=2026-01-07").json()
    assert summary["source"] == "INTERNAL LEDGER"


def test_zero_nav_never_crashes_group_concentration_or_creates_zero_weights(
    client: TestClient,
) -> None:
    balance(client, bucket="other_liabilities", currency="SGD", amount="10000")
    data = exposures(client)
    assert D(data["nav"]) == 0
    row = data["groups"]["currency"][0]
    assert D(row["net_value"]) == 0
    assert D(row["gross_value"]) == 20000
    assert row["weight"] is row["gross_weight"] is None
    summary = client.get(BASE + "/summary?end=2026-01-07").json()
    assert summary["risk"]["max_sector_weight"] is None
    assert summary["risk"]["max_currency_weight"] is None


def test_negative_nav_preserves_signed_weights_and_positive_gross_denominator(
    client: TestClient,
) -> None:
    balance(client, bucket="other_liabilities", currency="SGD", amount="20000")
    data = exposures(client)
    assert D(data["nav"]) == -10000
    row = data["groups"]["currency"][0]
    assert D(row["weight"]) == 1
    assert D(row["gross_weight"]) == 3
    assert D(row["balance_value"]) == -20000


def test_exposure_snapshot_does_not_reprice_and_rejects_foreign_runs(
    client: TestClient,
    ledger_session: Session,
) -> None:
    trade(client)
    original = exposures(client)
    run_id = original["valuation_run_id"]
    for row in ledger_session.scalars(select(models.FxObservation)):
        row.rate = D(2)
    ledger_session.commit()
    path = BASE + "/exposures"
    assert client.get(path, params={"run_id": run_id}).json() == original
    assert exposures(client)["nav"] != original["nav"]
    assert client.get(path, params={"run_id": run_id, "end": "2026-01-07"}).status_code == 422
    assert client.get(path, params={"run_id": "missing"}).status_code == 404
    other = client.post(
        "/api/v1/portfolios",
        json={
            "code": "OTHER",
            "name": "Other book",
            "reference_capital": "100",
            "opening_date": "2026-01-05",
        },
    )
    assert other.status_code == 201
    assert (
        client.get(
            f"/api/v1/portfolios/{other.json()['id']}/exposures", params={"run_id": run_id}
        ).status_code
        == 404
    )


def test_legacy_exposure_snapshot_does_not_invent_modern_components(
    client: TestClient,
    ledger_session: Session,
) -> None:
    trade(client)
    current = client.get(BASE + "/summary?end=2026-01-07").json()
    payload = deepcopy(current)
    payload.pop("exposure_methodology")
    payload.pop("exposure_balances")
    payload["exposures"] = {"currency": [{"name": "USD", "value": "52", "weight": 0.005}]}
    payload["freshness"] = {
        "stale_market_value": "0",
        "stale_nav_pct": 0,
        "price_coverage_pct": 100,
    }
    payload["valuation_run_id"] = "old-exposures"
    payload["calculation_version"] = "knk-nav-4.4"
    ledger_session.add(
        models.PortfolioValuationRun(
            id="old-exposures",
            portfolio_id="book",
            fingerprint="old-exposures",
            valuation_date=date(2026, 1, 7),
            status="SUCCEEDED",
            nav=D(current["portfolio"]["nav"]),
            payload=payload,
        )
    )
    ledger_session.commit()
    data = client.get(BASE + "/exposures?run_id=old-exposures").json()
    assert data["state"] == "LEGACY_SNAPSHOT"
    assert data["groups"] == payload["exposures"]
    assert "cash_value" not in data["groups"]["currency"][0]
    assert data["methodology"] is None
    assert data["warnings"] == ["This historical run predates complete exposure components"]
