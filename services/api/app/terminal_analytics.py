from __future__ import annotations

import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .repositories import MarketRepository, PortfolioRepository
from .services import PortfolioService

FUNCTIONS = json.loads((Path(__file__).parent / "data" / "functions.json").read_text())
VERSION = "knk-analytics-2.0"


def safe_number(value):
    return float(value) if value is not None and math.isfinite(float(value)) else None


def instrument(session: Session, key: str):
    item = session.get(models.Instrument, key)
    if item is None:
        item = session.scalar(
            select(models.Instrument).where(models.Instrument.symbol == key.upper())
        )
    if item is None:
        raise ValueError("Security not found")
    return item


def price_frame(session: Session, ids: list[str], limit_days=3700):
    if session.scalar(
        select(models.MarketObservation.id)
        .where(models.MarketObservation.instrument_id.in_(ids))
        .limit(1)
    ):
        from .price_sources import MarketPriceResolver

        today = datetime.now(UTC).date()
        book = MarketPriceResolver(session, ids, today - timedelta(days=limit_days))
        values = [
            {"date": pd.Timestamp(row["date"]), "id": key, "close": row["close"]}
            for key in ids
            for row in book.history(key, today - timedelta(days=limit_days), today)
        ]
        return (
            pd.DataFrame(values)
            .pivot_table(index="date", columns="id", values="close", aggfunc="last")
            .sort_index()
            if values
            else pd.DataFrame()
        )
    latest = session.scalar(
        select(models.PriceBar.timestamp)
        .where(models.PriceBar.interval == "1d")
        .order_by(models.PriceBar.timestamp.desc())
        .limit(1)
    )
    if latest is None:
        return pd.DataFrame()
    rows = session.scalars(
        select(models.PriceBar)
        .where(
            models.PriceBar.instrument_id.in_(ids),
            models.PriceBar.interval == "1d",
            models.PriceBar.timestamp >= latest - timedelta(days=limit_days),
        )
        .order_by(models.PriceBar.timestamp)
    ).all()
    return (
        pd.DataFrame(
            [
                {"date": row.timestamp, "id": row.instrument_id, "close": float(row.close)}
                for row in rows
            ]
        )
        .pivot_table(index="date", columns="id", values="close", aggfunc="last")
        .sort_index()
        .ffill()
    )


def quotes(session: Session):
    rows = session.execute(
        select(models.Instrument, models.LatestQuote, models.Exchange)
        .join(models.LatestQuote, models.LatestQuote.instrument_id == models.Instrument.id)
        .outerjoin(models.Exchange, models.Exchange.id == models.Instrument.exchange_id)
    ).all()
    frame = price_frame(session, [item.id for item, _, _ in rows], 8)
    result = []
    for item, quote, exchange in rows:
        prices = frame[item.id].dropna() if item.id in frame else []
        previous = float(prices.iloc[-2]) if len(prices) > 1 else float(quote.price)
        result.append(
            {
                "id": item.id,
                "symbol": item.symbol,
                "name": item.name,
                "asset_class": item.asset_class,
                "currency": item.currency,
                "country": item.country,
                "sector": item.sector,
                "industry": item.industry,
                "exchange": exchange.code if exchange else None,
                "price": float(quote.price),
                "change": float(quote.price) - previous,
                "change_pct": float(quote.price) / previous - 1 if previous else None,
                "source": quote.provider,
                "quality": quote.quality,
                "as_of": quote.as_of.isoformat(),
                "market_state": "DEMO" if quote.quality == "DEMO DATA" else "EOD",
            }
        )
    from .price_sources import MarketPriceResolver

    at = datetime.now(UTC)
    book = MarketPriceResolver(session, [r["id"] for r in result])
    for row in result:
        observation = book.resolve(row["id"], at)
        if observation:
            previous = book.resolve(row["id"], observation.timestamp - timedelta(days=1))
            row.update(
                {
                    "price": float(observation.value),
                    "change": float(observation.value - previous.value) if previous else None,
                    "change_pct": float(observation.value / previous.value - 1)
                    if previous
                    else None,
                    "source": observation.source,
                    "quality": observation.provenance(at)["data_state"],
                    "as_of": observation.timestamp.isoformat(),
                    "market_state": "DEMO"
                    if observation.category == "DEMO"
                    else "FILE IMPORT"
                    if observation.category == "FILE"
                    else observation.state,
                }
            )
        else:
            row.update(
                {
                    "price": None,
                    "change": None,
                    "change_pct": None,
                    "source": "UNAVAILABLE",
                    "quality": "UNAVAILABLE",
                    "as_of": None,
                    "market_state": "UNAVAILABLE",
                }
            )
    return result


def history(session: Session, key: str, limit=2600):
    item = instrument(session, key)
    if session.scalar(
        select(models.MarketObservation.id)
        .where(models.MarketObservation.instrument_id == item.id)
        .limit(1)
    ):
        from .price_sources import MarketPriceResolver

        today = datetime.now(UTC).date()
        book = MarketPriceResolver(session, [item.id])
        rows = book.history(item.id, today - timedelta(days=limit * 2), today)[-limit:]
        return {
            "instrument_id": item.id,
            "symbol": item.symbol,
            "source": rows[-1]["source"] if rows else None,
            "quality": rows[-1]["data_state"] if rows else "UNAVAILABLE",
            "as_of": rows[-1]["as_of"] if rows else None,
            "items": rows,
        }
    rows = session.scalars(
        select(models.PriceBar)
        .where(models.PriceBar.instrument_id == item.id, models.PriceBar.interval == "1d")
        .order_by(models.PriceBar.timestamp.desc())
        .limit(limit)
    ).all()[::-1]
    return {
        "instrument_id": item.id,
        "symbol": item.symbol,
        "source": rows[-1].provider if rows else None,
        "quality": rows[-1].quality if rows else "UNAVAILABLE",
        "as_of": rows[-1].timestamp.isoformat() if rows else None,
        "items": [
            {
                "date": bar.timestamp.date().isoformat(),
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": float(bar.volume or 0),
            }
            for bar in rows
        ],
    }


def portfolio_analytics(session: Session):
    from .broker_api import account_view
    from .portfolio_valuation import PortfolioValuationService

    return account_view(session, PortfolioValuationService(session).latest())


def legacy_portfolio_analytics(session: Session):
    snapshot = PortfolioService(session).default_snapshot()
    repo = PortfolioRepository(session)
    portfolio = repo.default_portfolio()
    holdings = repo.positions(portfolio.id)
    transactions = repo.transactions(portfolio.id)
    spy = instrument(session, "SPY")
    ids = sorted(
        {p.instrument_id for p in holdings}
        | {t.instrument_id for t in transactions if t.instrument_id}
        | {spy.id}
    )
    frame = price_frame(session, ids, 730)
    daily = frame.pct_change().dropna()
    nav = float(snapshot["portfolio"]["nav"])
    weights = {p.instrument_id: float(p.market_value) / nav if nav else 0 for p in holdings}
    weighted = sum(
        (daily[key] * weight for key, weight in weights.items()), pd.Series(0.0, index=daily.index)
    )
    benchmark = daily[spy.id]
    beta = float(weighted.cov(benchmark) / benchmark.var()) if benchmark.var() > 0 else 0.0
    quantile = float(weighted.quantile(0.05)) if len(weighted) else 0
    tail = weighted[weighted <= quantile]
    quotes_by_id = {q["id"]: q for q in quotes(session)}
    positions = []
    for p in snapshot["positions"]:
        quote = quotes_by_id[p["instrument_id"]]
        series = daily[p["instrument_id"]]
        p_beta = float(series.cov(benchmark) / benchmark.var()) if benchmark.var() > 0 else 0
        positions.append(
            {
                **p,
                **{k: quote[k] for k in ("currency", "sector", "country", "source", "as_of")},
                "beta": p_beta,
                "daily_pnl": float(p["market_value"]) * quote["change_pct"],
                "fx_rate": float(
                    MarketRepository(session).fx_rate(quote["currency"], portfolio.base_currency)
                ),
                "risk_contribution": float(p["weight"]) * p_beta,
            }
        )

    # Replay the recorded ledger against historical closes. Cash flows are removed from TWR.
    start = min(t.trade_date for t in transactions)
    dates = [d for d in frame.index if d.date() >= start]
    cash, quantities, curve, returns = 0.0, {}, [], []
    txn_index, previous_nav, peak, twr = 0, 0.0, 0.0, 1.0
    fx_rows = session.scalars(
        select(models.FxRate)
        .where(
            models.FxRate.base_currency == "USD",
            models.FxRate.quote_currency == portfolio.base_currency,
        )
        .order_by(models.FxRate.date)
    ).all()
    fx_by_date = {r.date: float(r.rate) for r in fx_rows}
    for day in dates:
        flows = 0.0
        while txn_index < len(transactions) and transactions[txn_index].trade_date <= day.date():
            txn = transactions[txn_index]
            amount = float(txn.quantity * txn.price * txn.fx_rate_to_base)
            if txn.transaction_type == "DEPOSIT":
                amount = amount or float(portfolio.reference_capital)
                cash += amount
                flows += amount
            elif txn.transaction_type == "BUY":
                quantities[txn.instrument_id] = quantities.get(txn.instrument_id, 0) + float(
                    txn.quantity
                )
                cash -= amount + float(txn.fee)
            elif txn.transaction_type == "SELL":
                quantities[txn.instrument_id] = quantities.get(txn.instrument_id, 0) - float(
                    txn.quantity
                )
                cash += amount - float(txn.fee)
            elif txn.transaction_type == "DIVIDEND":
                cash += amount
            elif txn.transaction_type == "FEE":
                cash -= float(txn.fee)
            txn_index += 1
        value = cash + sum(
            qty
            * float(frame.loc[day, key])
            * (fx_by_date.get(day.date(), 1.0) if quotes_by_id[key]["currency"] == "USD" else 1)
            for key, qty in quantities.items()
            if key in frame
        )
        ret = (value - flows) / previous_nav - 1 if previous_nav > 0 else 0.0
        returns.append(ret)
        twr *= 1 + ret
        peak = max(peak, value)
        curve.append(
            {
                "date": day.date().isoformat(),
                "equity": round(value, 2),
                "benchmark": float(portfolio.reference_capital)
                * float(frame.loc[day, spy.id] / frame.loc[dates[0], spy.id]),
                "drawdown": value / peak - 1 if peak else 0,
                "return": ret,
            }
        )
        previous_nav = value
    r = pd.Series(returns, dtype=float)
    down = r[r < 0]
    std = float(r.std(ddof=0)) if len(r) else 0
    periods = max((dates[-1] - dates[0]).days / 365.25, 1 / 365.25) if dates else 1
    performance = {
        "twr": twr - 1,
        "cagr": twr ** (1 / periods) - 1 if twr > 0 else -1,
        "volatility": std * math.sqrt(252),
        "sharpe": float(r.mean()) / std * math.sqrt(252) if std else 0,
        "sortino": float(r.mean()) / math.sqrt(float((down**2).mean())) * math.sqrt(252)
        if len(down) and (down**2).mean()
        else 0,
        "max_drawdown": min((p["drawdown"] for p in curve), default=0),
        "daily": returns[-1] if returns else 0,
        "quality": "DEMO DATA",
        "as_of": curve[-1]["date"] if curve else None,
    }
    risks = {
        "beta": beta,
        "volatility": float(weighted.std(ddof=0)) * math.sqrt(252),
        "var_95": min(0, quantile * nav),
        "var_99": min(0, float(weighted.quantile(0.01)) * nav),
        "cvar_95": min(0, float(tail.mean()) * nav) if len(tail) else 0,
        "max_drawdown": performance["max_drawdown"],
        "gross_exposure": sum(abs(w) for w in weights.values()),
        "net_exposure": sum(weights.values()),
        "concentration": max(weights.values(), default=0),
        "quality": "DEMO DATA",
        "as_of": frame.index[-1].isoformat(),
    }
    monthly = []
    for month, group in (
        pd.DataFrame(curve).assign(month=lambda df: df.date.str[:7]).groupby("month")
    ):
        monthly.append({"month": month, "return": float((1 + group["return"]).prod() - 1)})
    return {
        **snapshot,
        "positions": positions,
        "performance": performance,
        "risk": risks,
        "curve": curve,
        "monthly": monthly,
        "correlation": {
            "symbols": [quotes_by_id[key]["symbol"] for key in ids],
            "values": daily[ids].corr().fillna(0).values.tolist(),
        },
        "source": "Recorded demo ledger / DemoProvider closes",
        "as_of": frame.index[-1].isoformat(),
        "quality": "DEMO DATA",
        "warnings": [
            "Synthetic prices and historical transaction prices are independent demo fixtures; returns are not investment performance.",
            "Risk uses current weights, daily historical simulation and spot FX; market data may predate manual entries.",
        ],
    }


SCENARIOS = [
    ("SPX -5%", "Equity", -0.05, 0, 0, "All"),
    ("SPX -10%", "Equity", -0.10, 0, 0, "All"),
    ("NASDAQ -15%", "Equity", -0.15, 0, 0, "Technology"),
    ("Technology -15%", "Sector", -0.15, 0, 0, "Technology"),
    ("Financials -10%", "Sector", -0.10, 0, 0, "Financials"),
    ("USD/SGD +5%", "Currency", 0, 0.05, 0, "All"),
    ("USD/SGD -5%", "Currency", 0, -0.05, 0, "All"),
    ("Rates +100bp", "Rates", 0, 0, 100, "All"),
    ("Rates -100bp", "Rates", 0, 0, -100, "All"),
    ("VIX +50%", "Volatility", 0, 0, 0, "Volatility"),
    ("Oil -20%", "Commodity", -0.20, 0, 0, "Energy"),
    ("Correlation convergence", "Systemic", -0.08, 0, 0, "All"),
    ("2008 crisis proxy", "Historical proxy", -0.40, 0.08, -100, "All"),
    ("COVID crash proxy", "Historical proxy", -0.30, 0.05, -100, "All"),
    ("2022 rate-shock proxy", "Historical proxy", -0.20, 0.06, 200, "All"),
    ("Combined risk-off", "Systemic", -0.15, -0.05, 100, "All"),
]


def scenario_library():
    return [
        {
            "id": str(i),
            "name": name,
            "category": category,
            "equity_shock": 0 if name == "Correlation convergence" else equity * 100,
            "fx_shock": fx * 100,
            "rates_bp": rate,
            "scope": scope,
            "model": "CORRELATION"
            if name == "Correlation convergence"
            else "VOLATILITY"
            if scope == "Volatility"
            else "LINEAR",
        }
        for i, (name, category, equity, fx, rate, scope) in enumerate(SCENARIOS)
    ]


def stress_result(session: Session, parameters: dict):
    from .stress_engine import calculate_stress

    data = parameters.get("_portfolio") or portfolio_analytics(session)
    return calculate_stress(data, parameters)


def fundamentals(session: Session, key: str):
    item = instrument(session, key)
    from .curated_fundamentals import curated_statements

    curated = curated_statements(session, item)
    if curated is not None:
        return curated
    row = session.scalar(
        select(models.FundamentalSnapshot).where(
            models.FundamentalSnapshot.instrument_id == item.id
        )
    )
    if row is None:
        from .config import get_settings

        if get_settings().knk_env not in {"local-demo", "test", "demo"}:
            return {
                "symbol": item.symbol,
                "unit": f"{item.currency} millions / shares in millions",
                "source": "UNAVAILABLE",
                "quality": "UNAVAILABLE",
                "as_of": None,
                "items": [],
                "warnings": [
                    "Import verified statements or configure a fundamentals provider; no production demo fallback."
                ],
            }
        quote = MarketRepository(session).latest_quote(item.id)
        # Deterministic synthetic statements. These are never presented as company filings.
        rng = np.random.default_rng(sum(ord(c) for c in item.symbol) + 3110)
        sales = float(rng.uniform(15000, 100000))
        statements = []
        for year in range(2021, 2026):
            sales *= float(rng.uniform(1.04, 1.18))
            statements.append(
                {
                    "year": str(year),
                    "revenue": round(sales, 2),
                    "gross_profit": round(sales * 0.43, 2),
                    "ebit": round(sales * 0.25, 2),
                    "net_income": round(sales * 0.20, 2),
                    "operating_cash_flow": round(sales * 0.28, 2),
                    "capex": round(sales * 0.05, 2),
                    "free_cash_flow": round(sales * 0.23, 2),
                    "assets": round(sales * 1.4, 2),
                    "debt": round(sales * 0.3, 2),
                    "cash": round(sales * 0.2, 2),
                    "shares": round(
                        sales * 0.2 / max(float(quote.price) / 25 if quote else 1, 1), 2
                    ),
                }
            )
        row = models.FundamentalSnapshot(
            instrument_id=item.id,
            source="DemoProvider synthetic financial statements",
            quality="DEMO DATA",
            as_of=datetime(2025, 12, 31, tzinfo=UTC),
            statements={"items": statements},
        )
        session.add(row)
        try:
            session.commit()
        except IntegrityError:
            # Concurrent first-load requests may create the same deterministic fixture.
            session.rollback()
            row = session.scalar(
                select(models.FundamentalSnapshot).where(
                    models.FundamentalSnapshot.instrument_id == item.id
                )
            )
            if row is None:
                raise
    return {
        "symbol": item.symbol,
        "unit": f"{item.currency} millions, except per-share values",
        "source": row.source,
        "quality": row.quality,
        "as_of": row.as_of.isoformat(),
        **row.statements,
    }


def valuation(session: Session, key: str, growth=0.08, wacc=0.10, terminal_growth=0.025):
    if not -0.5 <= growth <= 0.5 or not 0.01 <= wacc <= 0.5 or not -0.05 <= terminal_growth < wacc:
        raise ValueError("Growth must be -50% to 50%; WACC must exceed terminal growth")
    data = fundamentals(session, key)
    eligible = [
        r
        for r in data["items"]
        if r.get("actual_estimate", "ACTUAL") == "ACTUAL"
        and r.get("frequency", "ANNUAL") in {"ANNUAL", "FY", "YEARLY"}
    ]
    if not eligible:
        raise ValueError("DCF requires annual actual financial statements")
    latest = eligible[-1]
    if (
        any(latest.get(k) is None for k in ("free_cash_flow", "debt", "cash", "shares"))
        or latest["shares"] <= 0
    ):
        raise ValueError(
            "DCF requires complete FCF, debt, cash and positive share count; missing imported fields are not replaced with demo values"
        )
    forecast = [
        {
            "year": i,
            "fcf": latest["free_cash_flow"] * (1 + growth) ** i,
            "pv": latest["free_cash_flow"] * (1 + growth) ** i / (1 + wacc) ** i,
        }
        for i in range(1, 6)
    ]
    terminal = forecast[-1]["fcf"] * (1 + terminal_growth) / (wacc - terminal_growth)
    enterprise = sum(r["pv"] for r in forecast) + terminal / (1 + wacc) ** 5
    equity = enterprise - latest["debt"] + latest["cash"]
    return {
        **data,
        "forecast": forecast,
        "enterprise_value": enterprise,
        "equity_value": equity,
        "fair_value": equity / latest["shares"],
        "growth": growth,
        "wacc": wacc,
        "terminal_growth": terminal_growth,
    }


def factor_analysis(session: Session, lookback=63, factor="MOMENTUM", horizon=5, cost_bps=10):
    universe = [q for q in quotes(session) if q["asset_class"] in ("Equity", "ETF")]
    if (
        not 5 <= lookback <= 500
        or not 1 <= horizon <= 63
        or not math.isfinite(cost_bps)
        or not 0 <= cost_bps <= 500
    ):
        raise ValueError("Invalid factor lookback, horizon or cost assumption")
    frame = pd.DataFrame(
        {
            q["id"]: pd.Series(
                {
                    pd.Timestamp(row["date"]): row["close"]
                    for row in history(session, q["id"], 800)["items"]
                    if not row.get("as_of")
                    or pd.Timestamp(row["as_of"]).date() == pd.Timestamp(row["date"]).date()
                },
                dtype=float,
            )
            for q in universe
        }
    ).sort_index()
    if lookback < 5 or len(frame) <= lookback + 1:
        return {
            "items": [],
            "lookback": lookback,
            "source": "SOURCE-AWARE HISTORY",
            "as_of": None,
            "quality": "INSUFFICIENT DATA",
            "diagnostics": {
                "state": "INSUFFICIENT DATA",
                "warnings": ["Requested factor lookback exceeds available history"],
            },
            "warnings": ["Requested factor lookback exceeds available history"],
        }
    from .factor_statistics import factor_signals, factor_statistics

    benchmark = next((q["id"] for q in universe if q["symbol"] == "SPY"), None)
    signal = (
        factor_signals(frame, lookback, factor, benchmark)
        .iloc[-1]
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    winsorised = signal.clip(signal.quantile(0.025), signal.quantile(0.975))
    zscore = (
        (winsorised - winsorised.mean()) / winsorised.std() if winsorised.std() else winsorised * 0
    )
    ranked = sorted(
        [q for q in universe if q["id"] in signal], key=lambda q: signal[q["id"]], reverse=True
    )
    rows = [
        {
            "symbol": q["symbol"],
            "sector": q["sector"],
            "country": q["country"],
            "factor": safe_number(signal[q["id"]]),
            "winsorised": safe_number(winsorised[q["id"]]),
            "zscore": safe_number(zscore[q["id"]]),
            "rank": i + 1,
            "quantile": 5 - min(4, i * 5 // len(ranked)),
            "volatility": safe_number(
                frame[q["id"]].pct_change(fill_method=None).std() * math.sqrt(252)
            ),
            "source": q["source"],
            "quality": q["quality"],
            "as_of": q["as_of"],
        }
        for i, q in enumerate(ranked)
    ]
    diagnostics = factor_statistics(frame, lookback, horizon, factor, benchmark, cost_bps)
    return {
        "items": rows,
        "lookback": lookback,
        "factor": factor,
        "source": " / ".join(sorted({q["source"] for q in universe})),
        "as_of": frame.index[-1].isoformat(),
        "quality": "DEMO DATA"
        if all(q["market_state"] == "DEMO" for q in universe)
        else "MIXED SOURCES",
        "diagnostics": diagnostics,
        "warnings": diagnostics["warnings"]
        + [
            "Source-aware native-currency technical factors. Latest signals have no observable forward return; historical IC is reported separately. No missing-price fill. Z-scores winsorise the latest cross-section at 2.5/97.5 percentiles."
        ],
    }
