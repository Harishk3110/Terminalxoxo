import pytest
from app import models
from app.hedge_engine import HedgeRequest, HedgeService, size_hedge
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def book():
    return {
        "portfolio": {"nav": 100000},
        "risk": {"beta": 1.2, "gross_exposure": 1, "net_exposure": 1, "var_95": -2000},
        "positions": [{"symbol": "SPY", "market_value": 50000}],
        "exposures": {
            "sector": [{"name": "Technology", "weight": 0.6}],
            "currency": [{"name": "USD", "weight": 0.8}],
        },
    }


@pytest.fixture
def hedge():
    return {"price": 500, "fx": 1.3, "multiplier": 1, "beta": 1, "sector": "Technology"}


def test_beta_sizing_accounts_for_fx_rounding_existing_holding_and_costs(book, hedge):
    result = size_hedge(book, HedgeRequest(target=0.8, fee_bps=10, slippage_bps=5), hedge)
    assert result["units"] == -61
    assert result["signed_notional"] == -39650
    assert result["residual_notional"] == pytest.approx(-350)
    assert result["post_cost_nav"] == pytest.approx(99940.525)
    assert result["beta_after"] == pytest.approx((120000 - 39650) / 99940.525)
    assert result["gross_after"] == pytest.approx(60350 / 99940.525)
    assert result["var_after"] is None
    assert "NO ORDER" in result["warnings"][0]


def test_hedge_beta_is_not_assumed_one_and_direction_can_increase(book, hedge):
    hedge["beta"] = 2
    result = size_hedge(book, HedgeRequest(target=0.8), hedge)
    assert result["units"] == -30
    assert size_hedge(book, HedgeRequest(target=1.8), hedge)["units"] > 0
    hedge["beta"] = 0
    with pytest.raises(ValueError, match="nonzero"):
        size_hedge(book, HedgeRequest(), hedge)


def test_net_sector_currency_and_futures_estimates(book, hedge):
    assert (
        size_hedge(book, HedgeRequest(mode="NET", target=0.5), hedge)["required_notional"] == -50000
    )
    assert (
        size_hedge(book, HedgeRequest(mode="SECTOR", target=0.3), hedge)["required_notional"]
        == -30000
    )
    hedge.update(price=1, multiplier=1, beta=None)
    fx = size_hedge(
        book, HedgeRequest(mode="CURRENCY", instrument_type="FX_CONVERSION", target=0.5), hedge
    )
    assert fx["gross_after"] == fx["gross_before"]
    assert fx["currency_stress_impact"] < 0 and fx["equity_stress_impact"] is None
    hedge.update(price=5000, multiplier=5, beta=1)
    future = size_hedge(book, HedgeRequest(instrument_type="FUTURE_ESTIMATE", symbol="MES"), hedge)
    assert future["units"] == -1
    assert future["gross_after"] == 1.325


def test_invalid_sector_and_excessive_notional_rejected(book, hedge):
    with pytest.raises(ValueError, match="classified"):
        size_hedge(book, HedgeRequest(mode="SECTOR", sector="Financials"), hedge)
    hedge["beta"] = 0.0001
    with pytest.raises(ValueError, match="five times"):
        size_hedge(book, HedgeRequest(), hedge)


def test_saved_hedge_is_scoped_reviewable_and_does_not_change_ledger(
    ledger_session: Session, session_token: str
) -> None:
    user = ledger_session.scalar(select(models.User))
    service = HedgeService(ledger_session)
    parameters = HedgeRequest(
        mode="NET",
        instrument_type="FUTURE_ESTIMATE",
        symbol="MES",
        target=0.2,
        assumed_price=5000,
        assumed_beta=1,
        contract_multiplier=5,
    )
    before = list(ledger_session.scalars(select(models.PortfolioTransaction.id)))
    result = service.create("book", parameters, user.id)
    assert result["units"] == 0 and result["valuation_run_id"]
    assert result["hedge_inputs"]["price_provenance"]["data_state"] == "USER ASSUMPTION"
    reviewed = service.review("book", result["id"], "REVIEWED", "Manual review completed", user.id)
    ledger_session.commit()
    assert reviewed["review_state"] == "REVIEWED"
    run = ledger_session.get(models.AnalysisRun, result["id"])
    assert len(run.history) == 2
    assert list(ledger_session.scalars(select(models.PortfolioTransaction.id))) == before
    with pytest.raises(ValueError):
        service.review("book", "unknown", "REVIEWED", "Missing review record", user.id)
