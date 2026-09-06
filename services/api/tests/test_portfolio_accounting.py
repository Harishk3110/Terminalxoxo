from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app import models
from app.portfolio_engine import Entry, LedgerState, daily_performance, nav_total
from app.portfolio_seed import ANCHORS, ensure_main
from app.portfolio_valuation import PortfolioValuationService
from app.price_sources import MarketPriceResolver, FxRateResolver


D = Decimal
DAY = date(2026, 6, 3)


def entry(kind, **kwargs):
    defaults = dict(id=kind, day=DAY, kind=kind, currency="SGD")
    defaults.update(kwargs)
    return Entry(**defaults)


@pytest.fixture
def accounting_session():
    engine = create_engine("sqlite://")
    models.Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False, autoflush=False) as session:
        for symbol in ANCHORS:
            session.add(models.Instrument(symbol=symbol, name=symbol, country="Singapore" if symbol == "D05" else "United States", currency="SGD" if symbol in {"D05", "USD.SGD"} else "USD", asset_class="ETF" if symbol == "SPY" else "Equity", security_type="Common Stock", sector="Financials" if symbol == "D05" else "Technology"))
        session.flush()
        ensure_main(session)
        yield session
    engine.dispose()


def test_deposit_requires_explicit_amount():
    with pytest.raises(ValueError, match="explicit"):
        LedgerState().apply(entry("DEPOSIT"))
    state = LedgerState()
    state.apply(entry("DEPOSIT", amount=D("70000")))
    assert state.cash["SGD"] == state.external_flows == D("70000")


def test_average_cost_partial_sale_and_realised_pnl():
    state = LedgerState()
    state.apply(entry("DEPOSIT", amount=D("70000")))
    state.apply(entry("BUY", instrument_id="A", quantity=D("10"), price=D("100"), fee=D("1")))
    state.apply(entry("BUY", instrument_id="A", quantity=D("10"), price=D("120"), commission=D("2")))
    state.apply(entry("SELL", instrument_id="A", quantity=D("5"), price=D("130"), fee=D("1")))
    assert state.lots["A"].quantity == 15
    assert state.lots["A"].cost_native == D("1650")
    assert state.lots["A"].realised == D("100")
    assert state.cash["SGD"] == D("68446")
    assert state.fees == D("4")


def test_short_cover_cost_basis():
    state = LedgerState()
    state.apply(entry("DEPOSIT", amount=D("1000")))
    state.apply(entry("SHORT", instrument_id="A", quantity=D("10"), price=D("100")))
    state.apply(entry("COVER", instrument_id="A", quantity=D("4"), price=D("80")))
    assert state.lots["A"].quantity == -6
    assert state.lots["A"].cost_base == -600
    assert state.lots["A"].realised == 80
    assert state.cash["SGD"] == 1680
    with pytest.raises(ValueError):
        state.apply(entry("COVER", instrument_id="A", quantity=D("7"), price=D("80")))


def test_native_cash_fx_conversion_and_income():
    state = LedgerState()
    state.apply(entry("DEPOSIT", amount=D("70000")))
    state.apply(entry("FX_CONVERSION", amount=D("1300"), metadata={"to_currency": "USD", "to_amount": "1000"}))
    state.apply(entry("BUY", currency="USD", instrument_id="A", quantity=D("5"), price=D("100"), fx=D("1.3"), fee=D("2")))
    state.apply(entry("DIVIDEND", currency="USD", instrument_id="A", amount=D("10"), fx=D("1.3")))
    assert state.cash == {"SGD": D("68700"), "USD": D("508")}
    assert state.cash_book_base == D("69360.4")
    assert state.lots["A"].cost_base == 650
    assert state.income == 13
    assert state.fees == D("2.6")


@pytest.mark.parametrize("kind", ["FEE", "COMMISSION", "TAX"])
def test_expense_types(kind):
    state = LedgerState()
    state.apply(entry("DEPOSIT", amount=D("70000")))
    state.apply(entry(kind, amount=D("25")))
    assert state.cash["SGD"] == state.cash_book_base == 69975
    assert state.fees + state.taxes == 25


def test_split_and_spinoff_preserve_book_cost():
    state = LedgerState()
    state.apply(entry("BUY", instrument_id="A", quantity=D("10"), price=D("100")))
    state.apply(entry("SPLIT", instrument_id="A", metadata={"ratio": "2"}))
    assert state.lots["A"].quantity == 20
    state.apply(entry("SPINOFF", instrument_id="A", quantity=D("5"), metadata={"child_instrument_id": "B", "cost_allocation": ".25"}))
    assert state.lots["A"].cost_base == 750
    assert state.lots["B"].cost_base == 250


def test_transfers_and_correction_are_explicit():
    state = LedgerState()
    state.apply(entry("TRANSFER_IN", instrument_id="A", quantity=D("10"), price=D("100")))
    state.apply(entry("TRANSFER_OUT", instrument_id="A", quantity=D("4"), price=D("120")))
    assert state.external_flows == 520
    assert state.lots["A"].realised == 80
    with pytest.raises(ValueError, match="reason"):
        state.apply(entry("OTHER_ADJUSTMENT", amount=D("10")))
    state.apply(entry("OTHER_ADJUSTMENT", amount=D("10"), metadata={"reason": "Correction", "direction": "CREDIT"}))
    assert state.adjustments == 10


def test_nav_full_balance_sheet_and_flow_adjustment():
    result = nav_total(D("20000"), [D("51000"), D("-500")], {"accrued_income": D("100"), "receivables": D("200"), "payables": D("50"), "accrued_fees": D("20"), "other_liabilities": D("30")})
    assert result["nav"] == 70700
    pnl, ret = daily_performance(D("70000"), D("81000"), D("10000"))
    assert pnl == 1000
    assert ret == D(".0125")


def test_seed_nav_and_independent_reconciliation(accounting_session):
    service = PortfolioValuationService(accounting_session)
    opening = service.calculate(end=DAY)
    assert opening["portfolio"]["nav"] == "70000.00"
    result = service.latest(end=date(2026, 9, 4))
    assert result["portfolio"]["code"] == "KNK_MAIN"
    assert D(result["portfolio"]["reference_capital"]) == 70000
    assert D("65000") < D(result["portfolio"]["nav"]) < D("80000")
    assert result["reconciliation"]["difference"] == "0.00"
    assert result["reconciliation"]["state"] == "BALANCED"
    assert result["performance"]["cagr"] is None
    assert result["performance"]["mwr"] is not None
    assert len(result["curve"]) > 60
    assert result["correlation"]["symbols"] == sorted(result["correlation"]["symbols"])
    assert result["performance"]["twr"] == pytest.approx(float(D(result["portfolio"]["nav"]) / D("70000") - 1), abs=1e-7)
    frozen = service.latest(end=date(2026, 9, 4))
    assert frozen["valuation_run_id"] == result["valuation_run_id"]


def test_correlation_order_uses_symbols_and_undefined_values_are_missing():
    histories = {"first-id": {DAY: 100}, "second-id": {DAY: 200}}
    positions = [{"instrument_id": "first-id", "symbol": "ZZZ", "weight": .5},
                 {"instrument_id": "second-id", "symbol": "AAA", "weight": .5}]
    risk, correlation = PortfolioValuationService.risk(histories, positions, None, D("70000"), {})
    assert correlation["symbols"] == ["AAA", "ZZZ"]
    assert correlation["values"] == [[None, None], [None, None]]
    assert risk["beta"] is None


def test_stale_file_beats_newer_demo_and_missing_is_not_zero(accounting_session):
    item = accounting_session.scalar(select(models.Instrument).where(models.Instrument.symbol == "AAPL"))
    accounting_session.add(models.MarketObservation(instrument_id=item.id, timestamp=datetime(2026, 8, 20, tzinfo=timezone.utc), price=D("225"), currency="USD", source="KOYFIN FILE", source_category="FILE", data_state="FILE IMPORT", fields={"filename": "AAPL_2026-08-20.csv"}))
    accounting_session.commit()
    resolver = MarketPriceResolver(accounting_session, [item.id])
    at = datetime(2026, 9, 4, 22, tzinfo=timezone.utc)
    assert resolver.resolve(item.id, at).source == "KOYFIN FILE"
    assert resolver.describe(item.id, at)["data_state"] == "STALE"
    result = PortfolioValuationService(accounting_session).calculate(end=at.date())
    assert result["quality"] == "CALCULATED WITH STALE DATA"
    assert result["reconciliation"]["difference"] == "0.00"
    assert FxRateResolver(accounting_session).resolve("EUR", "SGD", at)[0] is None
    assert resolver.resolve("unknown", at) is None

def test_missing_selected_price_invalidates_complete_nav(accounting_session):
    item = accounting_session.scalar(select(models.Instrument).where(models.Instrument.symbol == "AAPL"))
    accounting_session.add(models.SourcePrecedenceRule(instrument_id=item.id, priority=["BROKER", "PROVIDER", "FILE", "DEMO"], preferred_source="Unavailable approved provider", stale_after_hours=72, reason="Explicit provider selection test"))
    accounting_session.commit()
    result = PortfolioValuationService(accounting_session).latest()
    assert result["portfolio"]["nav"] is None
    assert result["portfolio"]["market_value"] is None
    assert result["portfolio"]["gross_asset_value"] is None
    assert result["risk"]["beta"] is None
    assert result["risk"]["gross_exposure"] is None
    apple = next(p for p in result["positions"] if p["symbol"] == "AAPL")
    assert apple["market_value"] is None and apple["weight"] is None
    assert next(p for p in result["attribution"] if p["symbol"] == "AAPL")["total_pnl"] is None


def test_reset_archives_ledger_and_isolates_demo_prices(accounting_session):
    from app.portfolio_seed import reset_main_demo, profile_for
    original = profile_for(accounting_session)
    old_id = original.portfolio_id
    old_transactions = set(accounting_session.scalars(select(models.PortfolioTransaction.id)).all())
    item = accounting_session.scalar(select(models.Instrument).where(models.Instrument.symbol == "AAPL"))
    accounting_session.add(models.MarketObservation(instrument_id=item.id, timestamp=datetime(2026, 9, 4, tzinfo=timezone.utc), price=D("1000"), currency="USD", source="KOYFIN FILE", source_category="FILE", data_state="FILE IMPORT", fields={}))
    accounting_session.commit()
    reset_main_demo(accounting_session)
    new = profile_for(accounting_session)
    assert new.portfolio_id != old_id and new.configuration["price_mode"] == "DEMO_ONLY"
    assert old_transactions <= set(accounting_session.scalars(select(models.PortfolioTransaction.id)).all())
    result = PortfolioValuationService(accounting_session).latest()
    assert D("69000") < D(result["portfolio"]["nav"]) < D("72000")
    assert result["reconciliation"]["difference"] == "0.00"
