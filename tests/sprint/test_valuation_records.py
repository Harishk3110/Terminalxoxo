"""Exact valuation records and explicit failure for incomplete transaction postings."""

from collections.abc import Iterable
from datetime import date
from decimal import Decimal as D

import pytest
from app import models, portfolio_valuation
from app.portfolio_domain.position_metrics import PortfolioPositionService
from app.portfolio_domain.postings import AccountingPosting, summarize_postings
from app.portfolio_domain.types import Lot
from app.portfolio_operations import PortfolioLedgerService
from app.portfolio_valuation import PortfolioValuationService
from app.valuation_records import ValuationPosition
from app.valuation_values import jsonable
from pydantic import TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def test_position_payload_preserves_exact_amounts_and_field_order() -> None:
    measured = PortfolioPositionService.measure(
        Lot(quantity=D(10), cost_native=D(1000), cost_base=D(1300)), D(120), D("1.4")
    )
    row = measured.payload()
    expected = {
        "direction": "LONG",
        "quantity": "10",
        "contract_multiplier": "1",
        "average_cost": "100",
        "cost_basis_native": "1000",
        "cost_basis_base": "1300",
        "market_price": "120",
        "market_value_native": "1200",
        "market_value_base_exact": "1680.0",
        "market_value": "1680.00",
        "unrealised_pnl_native": "200",
        "unrealised_pnl": "380.00",
        "unrealised_price_pnl_base": "280.0",
        "unrealised_fx_pnl_base": "100.0",
        "realised_pnl": "0.00",
        "income": "0.00",
        "fees": "0.00",
        "capitalized_charges": "0.00",
        "expensed_charges": "0.00",
        "total_pnl": "380.00",
        "return": str(D(380) / D(1300)),
        "valuation_state": "AVAILABLE",
        "valuation_warnings": [],
        "unrealised_decomposition_method": "Price component = (native market value - native basis) x current FX; FX component = native basis x current FX - recorded base basis",
    }
    assert jsonable(row) == expected
    assert list(row) == list(expected)
    assert isinstance(row["market_value_base_exact"], D)
    assert isinstance(row["return"], D)


@pytest.mark.parametrize(
    "name",
    ["external_flows", "income", "fees_paid", "taxes", "capitalized_charges", "expensed_fees"],
)
def test_missing_transaction_posting_total_cannot_persist_a_successful_valuation(
    ledger_session: Session, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    def incomplete(rows: Iterable[AccountingPosting]) -> dict[str, D | None]:
        result = summarize_postings(rows)
        result[name] = None
        return result

    monkeypatch.setattr(portfolio_valuation, "summarize_postings", incomplete)
    with pytest.raises(ValueError, match="Recorded transaction posting total is unavailable"):
        PortfolioValuationService(ledger_session).latest("book", end=date(2026, 1, 7))
    assert ledger_session.scalar(select(func.count(models.PortfolioValuationRun.id))) == 0
    assert ledger_session.scalar(select(func.count(models.PortfolioTransaction.id))) == 1


@pytest.mark.parametrize("weight", [None, D(0)])
def test_risk_distinguishes_missing_weight_from_a_recorded_zero_weight(
    ledger_session: Session, weight: D | None
) -> None:
    PortfolioLedgerService(ledger_session).add(
        {
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": "1",
            "price": "120",
        },
        "TEST_BOOK",
    )
    data = PortfolioValuationService(ledger_session).latest("book", end=date(2026, 1, 7))
    positions = TypeAdapter(list[ValuationPosition]).validate_python(data["positions"])
    assert len(positions) == 1
    positions[0]["weight"] = weight
    if weight is None:
        with pytest.raises(ValueError, match="Risk requires calculated position weights"):
            PortfolioValuationService.risk({}, positions, None, D(10000), {})
    else:
        metrics, correlation = PortfolioValuationService.risk({}, positions, None, D(10000), {})
        assert metrics["gross_exposure"] == metrics["net_exposure"] == 0
        assert metrics["beta"] is None
        assert correlation["model"]["state"] == "INSUFFICIENT_DATA"
        assert correlation["model"]["reason"]
        assert correlation["values"] == [[None]]
