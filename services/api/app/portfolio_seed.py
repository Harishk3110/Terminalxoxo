"""Deterministic, internally consistent KNK_MAIN seed; legacy portfolios are retained."""
from __future__ import annotations

import math
import uuid
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, update
from . import models

DEMO_SOURCE = "KnK Demo / coherent daily series"
START = date(2026, 5, 4)
END = date(2026, 9, 4)
OPENING = date(2026, 6, 3)
ANCHORS = {
    "AAPL": 210, "MSFT": 410, "NVDA": 125, "AMZN": 185, "GOOGL": 165,
    "META": 520, "JPM": 205, "XOM": 115, "UNH": 480, "V": 265,
    "SPY": 560, "QQQ": 480, "IWM": 210, "TLT": 94, "GLD": 240,
    "EWS": 26, "D05": 36, "ES": 5700, "USD.SGD": 1.29, "SPX": 5650,
}


def profile_for(session, key=None):
    query = select(models.PortfolioProfile)
    if key:
        query = query.where((models.PortfolioProfile.portfolio_id == key) | (models.PortfolioProfile.code == key))
    else:
        query = query.where(models.PortfolioProfile.code == "KNK_MAIN")
    return session.scalar(query)


def ensure_main(session, *, demo_only=False):
    existing = profile_for(session)
    if existing:
        return session.get(models.Portfolio, existing.portfolio_id)
    instruments = {r.symbol: r for r in session.scalars(select(models.Instrument)).all()}
    if not {"AAPL", "MSFT", "SPY", "D05"}.issubset(instruments):
        raise ValueError("Seed the security master before the main portfolio")
    values = {}
    has_prices = session.scalar(select(models.MarketObservation.id).where(models.MarketObservation.source == DEMO_SOURCE).limit(1))
    day, index = START, 0
    while day <= END:
        if day.weekday() < 5:
            stamp = datetime.combine(day, time(20), timezone.utc)
            fx = Decimal(str(1.29 + .004 * math.sin(index / 11))).quantize(Decimal(".00000001"))
            if not has_prices:
                session.add(models.FxObservation(base_currency="USD", quote_currency="SGD", timestamp=stamp, rate=fx, source=DEMO_SOURCE, source_category="DEMO", data_state="DEMO"))
            values[("FX", day)] = fx
            for offset, (symbol, anchor) in enumerate(ANCHORS.items()):
                if symbol not in instruments:
                    continue
                price = Decimal(str(anchor * (1 + .00035 * index + .009 * math.sin(index * .34) + .003 * math.sin(index * (.20 + offset * .025))))).quantize(Decimal(".0001"))
                if symbol == "USD.SGD":
                    price = fx
                values[(symbol, day)] = price
                if not has_prices:
                    session.add(models.MarketObservation(
                        instrument_id=instruments[symbol].id, timestamp=stamp, price=price,
                        currency=instruments[symbol].currency, source=DEMO_SOURCE,
                        source_category="DEMO", data_state="DEMO", adjustment_state="SYNTHETIC",
                        fields={"open": str(price * Decimal(".999")), "high": str(price * Decimal("1.004")), "low": str(price * Decimal(".996")), "close": str(price), "volume": 1000000 + index * 137},
                    ))
            index += 1
        day += timedelta(days=1)

    session.execute(update(models.Portfolio).values(is_default=False))
    portfolio = models.Portfolio(name="KnK Capital Main Portfolio", base_currency="SGD", reference_capital=Decimal("70000"), is_default=True)
    session.add(portfolio)
    session.flush()
    account = models.PortfolioAccount(portfolio_id=portfolio.id, account_type="MANUAL", display_name="KnK proprietary capital / manual ledger", provider="INTERNAL LEDGER")
    session.add(account)
    profile = models.PortfolioProfile(
        portfolio_id=portfolio.id, code="KNK_MAIN", is_demo=True,
        configuration={"execution_mode": "MANUAL", "broker_mode": "IBKR PAPER", "portfolio_type": "PROPRIETARY CAPITAL", "external_clients": 0, "benchmark": "SPY", "opening_date": OPENING.isoformat(), "price_mode": "DEMO_ONLY" if demo_only else "AUTO", "allow_short": True, "risk_free_rate": 0},
    )
    session.add(profile)
    session.flush()

    def add(kind, day, symbol=None, qty="0", amount="0", fee="0", metadata=None):
        native = "SGD" if not symbol else instruments[symbol].currency
        price = values.get((symbol, day), Decimal("0"))
        fx = values[("FX", day)] if native == "USD" else Decimal("1")
        quantity = Decimal(qty)
        gross = Decimal(amount) if Decimal(amount) else quantity * price
        txn = models.PortfolioTransaction(
            portfolio_id=portfolio.id, account_id=account.id,
            instrument_id=instruments[symbol].id if symbol else None,
            transaction_type=kind, trade_date=day, settle_date=day,
            quantity=quantity, price=price, currency=native, fx_rate_to_base=fx,
            fee=Decimal(fee), source="KNK_MAIN_DEMO", quality="DEMO DATA",
            notes=f"Deterministic {kind.lower()} / coherent price and FX history",
        )
        session.add(txn)
        session.flush()
        detail = models.TransactionDetail(
            transaction_id=txn.id, gross_amount=gross, commission=0, tax=0,
            contract_multiplier=1, base_value=gross * fx,
            metadata_json=metadata or {}, reconciliation_state="INTERNAL_ONLY",
        )
        session.add(detail)
        event = models.TradeEvent(portfolio_id=portfolio.id, transaction_id=txn.id, event_type=kind, source=txn.source, review_state="REVIEWED", payload={"demo_seed": True, "thesis": "Deterministic portfolio demonstration; not an investment recommendation"})
        session.add(event)
        return txn, detail

    add("DEPOSIT", OPENING, amount="70000")
    converted = (Decimal("45000") / values[("FX", OPENING)]).quantize(Decimal(".00000001"))
    add("FX_CONVERSION", OPENING, amount="45000", metadata={"to_currency": "USD", "to_amount": str(converted)})
    for symbol, day, quantity in [
        ("AAPL", date(2026, 6, 4), "45"), ("MSFT", date(2026, 6, 8), "22"),
        ("SPY", date(2026, 6, 11), "20"), ("D05", date(2026, 6, 15), "250"),
    ]:
        add("BUY", day, symbol, quantity, fee="1.00")
    add("SELL", date(2026, 7, 10), "AAPL", "5", fee="1.00")
    dividend, detail = add("DIVIDEND", date(2026, 8, 14), "AAPL", "40")
    dividend.price = Decimal(".26")
    detail.gross_amount = Decimal("10.40")
    detail.base_value = detail.gross_amount * dividend.fx_rate_to_base
    add("FEE", date(2026, 8, 31), amount="35")
    policy = models.RiskPolicy(portfolio_id=portfolio.id, name="KnK initial review limits", enabled=True)
    session.add(policy)
    session.flush()
    for metric, threshold, direction in [("max_position_weight", ".30", "MAX"), ("max_sector_weight", ".60", "MAX"), ("max_currency_weight", ".85", "MAX"), ("gross_exposure", "1.20", "MAX"), ("beta", "1.10", "MAX"), ("cash_weight", "0", "MIN")]:
        session.add(models.RiskLimit(policy_id=policy.id, metric=metric, threshold=Decimal(threshold), direction=direction))
    session.add(models.AuditLog(action="KNK_MAIN_CREATED", resource_type="portfolio", resource_id=portfolio.id, correlation_id=str(uuid.uuid4()), metadata_json={"opening_contribution": "70000.00", "base_currency": "SGD", "legacy_portfolios_preserved": True, "demo_source": DEMO_SOURCE}))
    session.commit()
    return portfolio


def reset_main_demo(session, actor=None):
    old = profile_for(session)
    if not old or not old.is_demo:
        raise ValueError("Only the demonstration portfolio can be reset")
    portfolio = session.get(models.Portfolio, old.portfolio_id)
    old.code = f"ARCHIVE_{old.id[:12]}"
    portfolio.is_default = False
    portfolio.name = f"{portfolio.name} / archived"
    session.add(models.AuditLog(action="DEMO_PORTFOLIO_ARCHIVED", resource_type="portfolio", resource_id=portfolio.id, actor_user_id=actor, correlation_id=str(uuid.uuid4()), metadata_json={"reason": "Explicit administrator reset", "transactions_preserved": True}))
    session.flush()
    return ensure_main(session, demo_only=True)
