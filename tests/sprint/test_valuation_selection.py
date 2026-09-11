from datetime import date

import pytest
from app import models
from app.hedge_engine import HedgeRequest, HedgeService
from app.portfolio_operations import PortfolioLedgerService
from app.portfolio_valuation import PortfolioValuationService
from app.valuation_selection import ValuationSelection
from sqlalchemy import select


def test_historical_valuation_does_not_replace_current_projection(ledger_session):
    ledger = PortfolioLedgerService(ledger_session)
    for kind, day, quantity in [("BUY", "2026-01-06", "10"), ("SELL", "2026-01-09", "3")]:
        ledger.add(
            {
                "transaction_type": kind,
                "trade_date": day,
                "symbol": "AAA",
                "quantity": quantity,
                "price": "100",
            },
            "book",
        )
    valuation = PortfolioValuationService(ledger_session)
    current = valuation.latest("book", force=True)
    assert current["positions"][0]["quantity"] == "7.00000000"
    current_positions = list(ledger_session.scalars(select(models.PortfolioPosition.id)))
    current_cash = list(ledger_session.scalars(select(models.PortfolioCashBalance.id)))
    current_returns = list(ledger_session.scalars(select(models.DailyReturn.id)))
    current_nav = list(ledger_session.scalars(select(models.NavSnapshot.id)))
    historical = valuation.latest("book", end=date(2026, 1, 7))
    assert historical["positions"][0]["quantity"] == "10.00000000"
    assert historical["valuation_run_id"] != current["valuation_run_id"]
    assert list(ledger_session.scalars(select(models.PortfolioPosition.id))) == current_positions
    assert list(ledger_session.scalars(select(models.PortfolioCashBalance.id))) == current_cash
    assert list(ledger_session.scalars(select(models.DailyReturn.id))) == current_returns
    assert list(ledger_session.scalars(select(models.NavSnapshot.id))) == current_nav


@pytest.mark.parametrize(
    "values",
    [
        {"valuation_date": "2099-01-01"},
        {"valuation_date": "invalid"},
        {"valuation_date": 1},
        {"valuation_date": True},
        {"valuation_date": "2026-01-07T12:00:00Z"},
        {"valuation_date": "20260107"},
        {"valuation_date": "2026-01-07", "valuation_run_id": "saved"},
        {"valuation_run_id": ""},
    ],
)
def test_invalid_valuation_selection_fails_closed(values):
    with pytest.raises(ValueError):
        ValuationSelection.model_validate(values)
    with pytest.raises(ValueError):
        HedgeRequest.model_validate(values)


def test_future_direct_valuation_is_rejected(ledger_session):
    with pytest.raises(ValueError, match="future"):
        PortfolioValuationService(ledger_session).latest("book", end=date(2099, 1, 1))
    assert not list(ledger_session.scalars(select(models.PortfolioValuationRun)))


def test_dated_and_saved_hedges_keep_the_selected_valuation(ledger_session, session_token):
    user = ledger_session.scalar(select(models.User))
    settings = {
        "mode": "NET",
        "instrument_type": "FUTURE_ESTIMATE",
        "symbol": "MES",
        "target": 0.2,
        "assumed_price": 5000,
        "assumed_beta": 1,
        "contract_multiplier": 5,
    }
    service = HedgeService(ledger_session)
    dated = service.create(
        "book", HedgeRequest(**settings, valuation_date=date(2026, 1, 7)), user.id
    )
    saved = service.create(
        "book", HedgeRequest(**settings, valuation_run_id=dated["valuation_run_id"]), user.id
    )
    ledger_session.commit()
    assert dated["valuation_date"] == saved["valuation_date"] == "2026-01-07"
    assert dated["valuation_run_id"] == saved["valuation_run_id"]
    assert dated["signed_notional"] == saved["signed_notional"]
    run = ledger_session.get(models.AnalysisRun, dated["id"])
    assert run.parameters["valuation_date"] == "2026-01-07"
    assert run.parameters["_portfolio"]["valuation_run_id"] == dated["valuation_run_id"]
    with pytest.raises(ValueError, match="not found"):
        service.create("book", HedgeRequest(**settings, valuation_run_id="unknown"), user.id)


def test_stress_pins_dated_snapshot_and_rejects_invalid_selection(
    ledger_session, session_token, monkeypatch
):
    from app import terminal_api
    from app.database import get_session
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(terminal_api.router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    launched = []
    monkeypatch.setattr(terminal_api, "launch_worker", launched.append)
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        response = client.post(
            "/api/v1/terminal/runs",
            json={
                "kind": "stress",
                "name": "Dated fixture",
                "parameters": {
                    "portfolio": "book",
                    "valuation_date": "2026-01-07",
                    "equity_shock": 0,
                },
            },
        )
        assert response.status_code == 202, response.text
        run = ledger_session.get(models.AnalysisRun, response.json()["id"])
        assert run.parameters["_portfolio"]["curve"][-1]["date"] == "2026-01-07"
        assert run.parameters["_portfolio"]["valuation_run_id"]
        invalid = client.post(
            "/api/v1/terminal/runs",
            json={
                "kind": "stress",
                "name": "Future fixture",
                "parameters": {
                    "portfolio": "book",
                    "valuation_date": "2099-01-07",
                },
            },
        )
        assert invalid.status_code == 422
        assert launched == [run.id]
