from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import date, datetime, timezone
from datetime import timedelta
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from . import models
from .domain import (
    annualized_volatility,
    cagr,
    hedge_units,
    historical_cvar,
    historical_var,
    max_drawdown,
    moving_average_signals,
    quantize_money,
    residual_notional,
    sharpe_ratio,
    sortino_ratio,
    twr_from_returns,
)
from .object_storage import ObjectStorage
from .providers.fred import FredObservationsResponse, FredProvider, FredSeriesResponse, FredVintageDatesResponse
from .repositories import AnalyticsRepository, DatasetRepository, InstrumentRepository, JobRepository, MacroRepository, MarketRepository, PortfolioRepository, ProviderRepository, RawObjectRepository, StrategyRepository, SystemRepository


QUALITY_DEMO = "DEMO DATA"


def to_jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [to_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: to_jsonable(item) for key, item in value.items()}
    return value


class DemoIngestionService:
    def __init__(self, session: Session, storage: ObjectStorage | None = None):
        self.session = session
        self.storage = storage or ObjectStorage()
        self.instruments = InstrumentRepository(session)
        self.market = MarketRepository(session)
        self.macro = MacroRepository(session)
        self.raw = RawObjectRepository(session)
        self.providers = ProviderRepository(session)

    def seed(self, *, reset: bool = False) -> dict[str, int]:
        if reset:
            for model in reversed(models.Base.metadata.sorted_tables):
                self.session.execute(model.delete())
            self.session.flush()
        elif self.session.execute(select(models.Instrument.id).limit(1)).first():
            return SystemRepository(self.session).counts()

        self.providers.upsert_connection(
            provider_name="FRED",
            provider_type="macro",
            enabled=False,
            configured=False,
            state="NOT_CONFIGURED",
            capabilities=["test_connection", "search_series", "metadata", "observations", "vintages", "backfill"],
        )
        self.providers.upsert_connection(provider_name="DemoProvider", provider_type="multi_asset", enabled=True, configured=True, state="CONNECTED", capabilities=["market_data", "macro", "fundamentals", "portfolio"])
        self.providers.upsert_connection(provider_name="IBKR Paper Agent", provider_type="broker", enabled=True, configured=False, state="NOT_CONFIGURED", capabilities=["account_summary", "positions", "fills", "commissions", "read_only"])

        raw_payload = self._deterministic_payload()
        raw_bytes = json.dumps(raw_payload, sort_keys=True).encode("utf-8")
        stored = self.storage.put_bytes(key="raw/demo/seed.json", data=raw_bytes, content_type="application/json")
        raw_object = self.raw.create(provider="DemoProvider", dataset="deterministic-seed", object_key=stored.object_key, content_hash=stored.content_hash, content_type="application/json", size_bytes=stored.size_bytes, source_uri="local-demo", correlation_id="seed-demo")

        exchanges = {
            "NASDAQ": self.instruments.upsert_exchange("NASDAQ", "Nasdaq Stock Market", "United States", "America/New_York"),
            "NYSE": self.instruments.upsert_exchange("NYSE", "New York Stock Exchange", "United States", "America/New_York"),
            "ARCA": self.instruments.upsert_exchange("ARCA", "NYSE Arca", "United States", "America/New_York"),
            "SGX": self.instruments.upsert_exchange("SGX", "Singapore Exchange", "Singapore", "Asia/Singapore"),
            "CME": self.instruments.upsert_exchange("CME", "Chicago Mercantile Exchange", "United States", "America/Chicago"),
        }
        for code, name in [("SGD", "Singapore Dollar"), ("USD", "US Dollar"), ("HKD", "Hong Kong Dollar"), ("JPY", "Japanese Yen"), ("EUR", "Euro")]:
            self.instruments.upsert_currency(code, name)

        instrument_specs = [
            ("AAPL", "Apple Inc.", "NASDAQ", "USD", "Equity", "Common Stock", "Information Technology", "Consumer Electronics"),
            ("MSFT", "Microsoft Corporation", "NASDAQ", "USD", "Equity", "Common Stock", "Information Technology", "Software"),
            ("NVDA", "NVIDIA Corporation", "NASDAQ", "USD", "Equity", "Common Stock", "Information Technology", "Semiconductors"),
            ("AMZN", "Amazon.com Inc.", "NASDAQ", "USD", "Equity", "Common Stock", "Consumer Discretionary", "Internet Retail"),
            ("GOOGL", "Alphabet Inc.", "NASDAQ", "USD", "Equity", "Common Stock", "Communication Services", "Internet Content"),
            ("META", "Meta Platforms Inc.", "NASDAQ", "USD", "Equity", "Common Stock", "Communication Services", "Social Media"),
            ("JPM", "JPMorgan Chase & Co.", "NYSE", "USD", "Equity", "Common Stock", "Financials", "Banks"),
            ("XOM", "Exxon Mobil Corporation", "NYSE", "USD", "Equity", "Common Stock", "Energy", "Integrated Oil"),
            ("UNH", "UnitedHealth Group Incorporated", "NYSE", "USD", "Equity", "Common Stock", "Health Care", "Managed Care"),
            ("V", "Visa Inc.", "NYSE", "USD", "Equity", "Common Stock", "Financials", "Payments"),
            ("SPY", "SPDR S&P 500 ETF Trust", "ARCA", "USD", "ETF", "ETF", "ETF", "Large Cap Blend"),
            ("QQQ", "Invesco QQQ Trust", "NASDAQ", "USD", "ETF", "ETF", "ETF", "Large Cap Growth"),
            ("IWM", "iShares Russell 2000 ETF", "ARCA", "USD", "ETF", "ETF", "ETF", "Small Cap"),
            ("TLT", "iShares 20+ Year Treasury Bond ETF", "NASDAQ", "USD", "ETF", "ETF", "ETF", "Treasury Bonds"),
            ("GLD", "SPDR Gold Shares", "ARCA", "USD", "ETF", "ETF", "ETF", "Commodities"),
            ("EWS", "iShares MSCI Singapore ETF", "ARCA", "USD", "ETF", "ETF", "ETF", "Singapore Equity"),
            ("D05", "DBS Group Holdings Ltd", "SGX", "SGD", "Equity", "Common Stock", "Financials", "Banks"),
            ("ES", "E-mini S&P 500 Futures", "CME", "USD", "Future", "Index Future", "Index Futures", "Equity Index"),
            ("USD.SGD", "US Dollar / Singapore Dollar", "SGX", "SGD", "FX", "FX Pair", "FX", "Currency"),
            ("SPX", "S&P 500 Index", "NYSE", "USD", "Index", "Benchmark", "Index", "Large Cap"),
        ]
        instruments: dict[str, models.Instrument] = {}
        for symbol, name, exchange, currency, asset_class, security_type, sector, industry in instrument_specs:
            instruments[symbol] = self.instruments.upsert_instrument(
                symbol=symbol,
                name=name,
                exchange_id=exchanges[exchange].id,
                country="Singapore" if exchange == "SGX" else "United States",
                currency=currency,
                asset_class=asset_class,
                security_type=security_type,
                sector=sector,
                industry=industry,
                is_active=True,
            )
            if not self.session.execute(select(models.ProviderInstrumentMapping).where(and_(models.ProviderInstrumentMapping.provider == "DemoProvider", models.ProviderInstrumentMapping.provider_symbol == symbol))).scalars().first():
                self.session.add(models.ProviderInstrumentMapping(instrument_id=instruments[symbol].id, provider="DemoProvider", provider_symbol=symbol, provider_metadata={"quality": QUALITY_DEMO}))

        start = date(2016, 9, 5)
        end = date(2026, 9, 4)
        day_count = 0
        latest_prices: dict[str, Decimal] = {}
        current = start
        while current <= end:
            if current.weekday() < 5:
                for idx, (symbol, *_rest) in enumerate(instrument_specs):
                    base = Decimal("40") + Decimal(idx * 17)
                    drift = Decimal(day_count) * (Decimal("0.006") + Decimal(idx) / Decimal("10000"))
                    cycle = Decimal(((day_count + idx * 7) % 31) - 15) / Decimal("100")
                    close = (base + drift) * (Decimal("1") + cycle / Decimal("10"))
                    open_price = close * Decimal("0.997")
                    high = close * Decimal("1.012")
                    low = close * Decimal("0.988")
                    instrument = instruments[symbol]
                    self.market.insert_price_bar(
                        instrument_id=instrument.id,
                        timestamp=datetime(current.year, current.month, current.day, tzinfo=timezone.utc),
                        interval="1d",
                        open=quantize_money(open_price),
                        high=quantize_money(high),
                        low=quantize_money(low),
                        close=quantize_money(close),
                        volume=Decimal(1_000_000 + idx * 50_000 + day_count),
                        currency=instrument.currency,
                        provider="DemoProvider",
                        quality=QUALITY_DEMO,
                        raw_object_id=raw_object.id,
                    )
                    latest_prices[symbol] = quantize_money(close)
                usdsgd = Decimal("1.31") + Decimal((day_count % 80) - 40) / Decimal("10000")
                self.market.upsert_fx("USD", "SGD", current, usdsgd, "DemoProvider", QUALITY_DEMO)
                self.market.upsert_fx("SGD", "USD", current, Decimal("1") / usdsgd, "DemoProvider", QUALITY_DEMO)
                day_count += 1
            current = date.fromordinal(current.toordinal() + 1)

        for symbol, price in latest_prices.items():
            instrument = instruments[symbol]
            self.market.upsert_quote(instrument.id, price, instrument.currency, datetime(2026, 9, 4, 21, 0, tzinfo=timezone.utc), "DemoProvider", QUALITY_DEMO)

        self._seed_intraday(instruments, raw_object.id)
        self._seed_macro(raw_object.id)
        self._seed_data_operations(raw_object.id)
        portfolio_id = self._seed_portfolio(instruments)
        self._seed_research_quant_alerts(instruments)
        portfolio_service = PortfolioService(self.session)
        portfolio_service.recalculate(portfolio_id)
        PerformanceService(self.session).calculate(portfolio_id)
        RiskService(self.session).calculate(portfolio_id)
        BacktestService(self.session).run_demo_backtest()
        self.session.commit()
        return SystemRepository(self.session).counts()

    def _deterministic_payload(self) -> dict:
        return {"seed": 3110, "date": "2026-09-05", "quality": QUALITY_DEMO, "provider": "DemoProvider"}

    def _seed_intraday(self, instruments: dict[str, models.Instrument], raw_object_id: str) -> None:
        start = datetime(2026, 6, 8, 13, tzinfo=timezone.utc)
        symbols = ["AAPL", "MSFT", "SPY", "D05"]
        for hour in range(90 * 7):
            ts = start + timedelta(hours=hour)
            for idx, symbol in enumerate(symbols):
                if ts.weekday() >= 5:
                    continue
                price = Decimal("100") + Decimal(idx * 40) + Decimal(hour) / Decimal("15")
                self.market.insert_price_bar(
                    instrument_id=instruments[symbol].id,
                    timestamp=ts,
                    interval="1h",
                    open=quantize_money(price * Decimal("0.999")),
                    high=quantize_money(price * Decimal("1.004")),
                    low=quantize_money(price * Decimal("0.996")),
                    close=quantize_money(price),
                    volume=Decimal(10000 + hour),
                    currency=instruments[symbol].currency,
                    provider="DemoProvider",
                    quality=QUALITY_DEMO,
                    raw_object_id=raw_object_id,
                )

    def _seed_macro(self, raw_object_id: str) -> None:
        watchlist = fred_default_watchlist()
        start = date(2016, 9, 30)
        for index, item in enumerate(watchlist):
            self.macro.upsert_series(
                series_id=item["series_id"],
                title=item["title"],
                units=item["units"],
                units_short=item["units_short"],
                frequency=item["frequency"],
                frequency_short=item["frequency_short"],
                seasonal_adjustment=item["seasonal_adjustment"],
                observation_start=start,
                observation_end=date(2026, 8, 31),
                last_updated="2026-09-05 00:00:00+00",
                popularity=80 - index,
                notes="Deterministic macro fixture following FRED-compatible schema.",
                provider="DemoProvider",
                quality=QUALITY_DEMO,
                raw_object_id=raw_object_id,
            )
            current = start
            obs_index = 0
            while current <= date(2026, 8, 31):
                value = Decimal("1.0") + Decimal(index) / Decimal("2") + Decimal(obs_index % 48) / Decimal("25")
                self.macro.insert_observation(
                    series_id=item["series_id"],
                    observation_date=current,
                    value=quantize_money(value),
                    units=item["units"],
                    realtime_start=current,
                    realtime_end=current,
                    vintage_date=current,
                    release_date=current,
                    provider="DemoProvider",
                    quality=QUALITY_DEMO,
                    raw_object_id=raw_object_id,
                )
                month = current.month + 1
                year = current.year + (month - 1) // 12
                month = ((month - 1) % 12) + 1
                current = date(year, month, 28)
                obs_index += 1

    def _seed_data_operations(self, raw_object_id: str) -> None:
        dataset = models.Dataset(name="demo-equity-prices", dataset_type="price_bars", source="DemoProvider", quality=QUALITY_DEMO)
        fundamentals = models.Dataset(name="demo-fundamentals", dataset_type="fundamentals", source="DemoProvider", quality=QUALITY_DEMO)
        self.session.add_all([dataset, fundamentals])
        self.session.flush()
        price_version = models.DatasetVersion(dataset_id=dataset.id, version=1, raw_object_id=raw_object_id, row_count=52260, content_hash="demo-price-bars-v1", schema_json={"columns": [{"name": "date", "type": "date"}, {"name": "symbol", "type": "string"}, {"name": "close", "type": "number"}]})
        fundamentals_version = models.DatasetVersion(dataset_id=fundamentals.id, version=1, raw_object_id=raw_object_id, row_count=80, content_hash="demo-fundamentals-v1", schema_json={"columns": [{"name": "period", "type": "date"}, {"name": "symbol", "type": "string"}, {"name": "revenue", "type": "number"}]})
        self.session.add_all([price_version, fundamentals_version])
        self.session.flush()
        for version in [price_version, fundamentals_version]:
            for column in version.schema_json.get("columns", []):
                self.session.add(models.DatasetColumn(dataset_version_id=version.id, name=column["name"], inferred_type=column["type"], mapped_role=column["name"]))
            self.session.add(models.DatasetLineage(dataset_version_id=version.id, source_type="raw_object", source_id=raw_object_id, transform="deterministic-demo-normalisation"))
        succeeded = models.IngestionJob(job_type="demo_market_close", provider="DemoProvider", parameters={"date": "2026-09-04"}, status="SUCCEEDED", progress=Decimal("1"), records_received=52260, records_accepted=52260, records_rejected=0, correlation_id="seed-demo-job-ok", worker_id="seed", started_at=datetime(2026, 9, 5, 0, 0, tzinfo=timezone.utc), finished_at=datetime(2026, 9, 5, 0, 1, tzinfo=timezone.utc))
        failed = models.IngestionJob(job_type="fred_refresh_default_watchlist", provider="FRED", parameters={"reason": "missing credentials"}, status="FAILED", progress=Decimal("1"), records_received=0, records_accepted=0, records_rejected=0, error_category="PROVIDER_NOT_CONFIGURED", error_message="FRED_API_KEY is not configured", correlation_id="seed-demo-job-fred", worker_id="seed", started_at=datetime(2026, 9, 5, 0, 2, tzinfo=timezone.utc), finished_at=datetime(2026, 9, 5, 0, 2, tzinfo=timezone.utc))
        self.session.add_all([succeeded, failed])
        self.session.flush()
        self.session.add_all(
            [
                models.IngestionJobRun(job_id=succeeded.id, state="SUCCEEDED", message="Demo price bars normalised", log_payload={"quality": QUALITY_DEMO}),
                models.IngestionJobRun(job_id=failed.id, state="FAILED", message="FRED credentials unavailable", log_payload={"state": "NOT_CONFIGURED"}),
                models.DataQualityIssue(dataset="FRED default watchlist", provider="FRED", severity="WARN", issue_type="PROVIDER_NOT_CONFIGURED", message="FRED backfill skipped until FRED_API_KEY is configured."),
                models.QuarantineRecord(dataset_version_id=price_version.id, row_number=0, payload={"symbol": "DEMO", "quality": QUALITY_DEMO}, error_message="Demo quarantine example for validation workflow"),
            ]
        )
        for component, state in [
            ("api", "ready"),
            ("postgres", "ready"),
            ("redis", "ready"),
            ("object_storage", "ready"),
            ("fred", "NOT_CONFIGURED"),
            ("worker-data", "ready"),
            ("worker-quant", "ready"),
            ("report-engine", "ready"),
        ]:
            self.session.add(models.SystemHealthSnapshot(component=component, state=state, details={"quality": QUALITY_DEMO}, checked_at=datetime(2026, 9, 5, 0, 5, tzinfo=timezone.utc)))

    def _seed_portfolio(self, instruments: dict[str, models.Instrument]) -> str:
        portfolio = models.Portfolio(name="KnK Capital Reference Portfolio", base_currency="SGD", reference_capital=Decimal("70000"), is_default=True)
        self.session.add(portfolio)
        self.session.flush()
        account = models.PortfolioAccount(portfolio_id=portfolio.id, account_type="REFERENCE", display_name="KnK SGD 70,000 Reference Account", provider="DemoProvider")
        self.session.add(account)
        self.session.flush()
        txns = [
            ("DEPOSIT", None, "2026-06-03", "0", "0", "SGD", "1", "70000 owner capital"),
            ("BUY", "AAPL", "2026-06-06", "45", "176.20", "USD", "1.345", "Initial quality growth allocation"),
            ("BUY", "MSFT", "2026-06-10", "22", "331.40", "USD", "1.344", "Software compounder allocation"),
            ("BUY", "SPY", "2026-06-17", "25", "514.80", "USD", "1.342", "Benchmark exposure"),
            ("DIVIDEND", "AAPL", "2026-08-16", "45", "0.26", "USD", "1.333", "Demo dividend"),
            ("FEE", None, "2026-08-31", "0", "0", "SGD", "1", "Monthly platform and data fee"),
            ("BUY", "D05", "2026-09-02", "300", "37.20", "SGD", "1", "Singapore home-market exposure"),
        ]
        for txn_type, symbol, trade_date, quantity, price, currency, fx, notes in txns:
            instrument_id = instruments[symbol].id if symbol else None
            fee = Decimal("7.50") if txn_type == "BUY" else (Decimal("35.00") if txn_type == "FEE" else Decimal("0"))
            self.session.add(
                models.PortfolioTransaction(
                    portfolio_id=portfolio.id,
                    account_id=account.id,
                    instrument_id=instrument_id,
                    transaction_type=txn_type,
                    trade_date=date.fromisoformat(trade_date),
                    settle_date=date.fromisoformat(trade_date),
                    quantity=Decimal(quantity),
                    price=Decimal(price),
                    currency=currency,
                    fx_rate_to_base=Decimal(fx),
                    fee=fee,
                    source="DemoProvider",
                    quality=QUALITY_DEMO,
                    notes=notes,
                )
            )
        return portfolio.id

    def _seed_research_quant_alerts(self, instruments: dict[str, models.Instrument]) -> None:
        watchlist = models.Watchlist(name="Core Demo Watchlist")
        self.session.add(watchlist)
        self.session.flush()
        for symbol in ["AAPL", "MSFT", "SPY", "D05"]:
            self.session.add(models.WatchlistItem(watchlist_id=watchlist.id, instrument_id=instruments[symbol].id))
        for title in ["Quality compounder thesis", "Macro disinflation thesis", "Singapore bank resilience thesis"]:
            thesis = models.InvestmentThesis(title=title, thesis_state="ACTIVE", summary=f"{title} uses deterministic demo data only.", instrument_id=None)
            self.session.add(thesis)
            self.session.flush()
            self.session.add(models.ThesisSource(thesis_id=thesis.id, source_type="demo-research", citation="KnK deterministic research fixture"))
        self.session.add(models.ResearchNote(instrument_id=instruments["MSFT"].id, title="Private demo thesis note", body="Private portfolio research note backed by deterministic demo data.", visibility="PRIVATE"))
        self.session.add(models.DecisionJournal(decision_type="REFERENCE_PORTFOLIO_SEED", rationale="Seeded SGD 70,000 reference portfolio for local deterministic acceptance."))
        strategy_specs = [
            ("Moving Average Crossover", "moving_average_crossover", {"fast": 20, "slow": 50}),
            ("RSI Threshold", "rsi_threshold", {"lower": 30, "upper": 70}),
            ("MACD Crossover", "macd_crossover", {"fast": 12, "slow": 26, "signal": 9}),
            ("Breakout", "breakout", {"lookback": 55}),
            ("Quality Momentum", "factor", {"quality_weight": 0.5, "momentum_weight": 0.5}),
            ("Low Volatility", "factor", {"lookback": 126}),
        ]
        for name, strategy_type, rules in strategy_specs:
            strategy = models.StrategyDefinition(name=name, strategy_type=strategy_type, description=f"{name} deterministic demo strategy.", status="AVAILABLE")
            self.session.add(strategy)
            self.session.flush()
            version = models.StrategyVersion(strategy_id=strategy.id, version=1, rules=rules)
            self.session.add(version)
        factor = models.FactorDefinition(name="Demo Momentum 126D", formula="close / close_126d - 1", description="Deterministic factor fixture.")
        self.session.add(factor)
        self.session.flush()
        factor_run = models.FactorRun(factor_id=factor.id, status="SUCCEEDED", started_at=datetime(2026, 9, 5, tzinfo=timezone.utc), finished_at=datetime(2026, 9, 5, 0, 1, tzinfo=timezone.utc))
        self.session.add(factor_run)
        self.session.flush()
        for index, symbol in enumerate(["AAPL", "MSFT", "SPY", "D05"]):
            self.session.add(models.FactorValue(factor_run_id=factor_run.id, instrument_id=instruments[symbol].id, date=date(2026, 9, 4), value=Decimal("0.05") + Decimal(index) / Decimal("100")))
        self.session.add(models.Alert(severity="WARN", title="Demo stale provider check", message="FRED is not configured; demo macro data remain active.", state="ACTIVE"))
        self.session.add(models.Alert(severity="INFO", title="Risk calculation completed", message="Reference risk snapshot calculated from deterministic data.", state="RESOLVED", acknowledged_at=datetime.now(timezone.utc)))


class PortfolioService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = PortfolioRepository(session)
        self.market = MarketRepository(session)

    def default_snapshot(self) -> dict:
        from .portfolio_seed import profile_for
        if profile_for(self.session):
            from .portfolio_valuation import PortfolioValuationService
            return PortfolioValuationService(self.session).latest()
        portfolio = self.repo.default_portfolio()
        if not portfolio:
            raise ValueError("Default portfolio not seeded")
        latest_nav = self.repo.latest_nav(portfolio.id)
        return {
            "portfolio": self._portfolio_payload(portfolio, latest_nav),
            "positions": [self._position_payload(position) for position in self.repo.positions(portfolio.id)],
            "cash": [self._cash_payload(item) for item in self.repo.cash(portfolio.id)],
            "transactions": [self._transaction_payload(item) for item in self.repo.transactions(portfolio.id)],
        }

    def add_manual_transaction(self, payload: dict) -> dict:
        from .portfolio_seed import profile_for
        if profile_for(self.session):
            from .portfolio_operations import PortfolioLedgerService
            result = PortfolioLedgerService(self.session).add({k: v for k, v in payload.items() if v is not None})
            self.session.commit()
            return result
        if payload["transaction_type"] not in {"BUY", "SELL", "DIVIDEND", "FEE", "DEPOSIT"}:
            raise ValueError("Unsupported manual ledger transaction")
        for field in ("quantity", "price", "fee", "fx_rate_to_base"):
            value = Decimal(str(payload.get(field, "0")))
            if not value.is_finite() or value < 0:
                raise ValueError(f"{field} must be finite and non-negative")
        if Decimal(str(payload.get("fx_rate_to_base", 1))) <= 0:
            raise ValueError("FX rate must be positive")
        if payload["transaction_type"] in {"BUY", "SELL"} and (not payload.get("symbol") or Decimal(str(payload.get("quantity", 0))) <= 0 or Decimal(str(payload.get("price", 0))) <= 0):
            raise ValueError("Security, positive quantity and positive price are required")
        portfolio = self.repo.default_portfolio()
        if not portfolio:
            raise ValueError("Default portfolio not seeded")
        instrument = None
        if payload.get("symbol"):
            instrument = InstrumentRepository(self.session).by_symbol(payload["symbol"])
            if instrument is None:
                raise ValueError(f"Unknown instrument {payload['symbol']}")
            if payload.get("currency") != instrument.currency:
                raise ValueError("Transaction currency must match the security currency")
        if payload["transaction_type"] == "SELL":
            trade_date = date.fromisoformat(payload["trade_date"])
            balance = Decimal("0")
            for existing in self.repo.transactions(portfolio.id):
                if existing.instrument_id == instrument.id and existing.trade_date <= trade_date:
                    if existing.transaction_type == "BUY":
                        balance += existing.quantity
                    elif existing.transaction_type == "SELL":
                        balance -= existing.quantity
            if Decimal(str(payload["quantity"])) > balance:
                raise ValueError("Sale exceeds recorded holdings on the trade date; short selling is not supported")
        txn = self.repo.add_transaction(
            portfolio_id=portfolio.id,
            account_id=None,
            instrument_id=instrument.id if instrument else None,
            transaction_type=payload["transaction_type"],
            trade_date=date.fromisoformat(payload["trade_date"]),
            settle_date=date.fromisoformat(payload.get("settle_date", payload["trade_date"])),
            quantity=Decimal(str(payload.get("quantity", "0"))),
            price=Decimal(str(payload.get("price", "0"))),
            currency=payload.get("currency") or portfolio.base_currency,
            fx_rate_to_base=Decimal(str(payload.get("fx_rate_to_base", "1"))),
            fee=Decimal(str(payload.get("fee", "0"))),
            source="MANUAL",
            quality=QUALITY_DEMO,
            notes=payload.get("notes"),
        )
        self.recalculate(portfolio.id)
        self.session.commit()
        return self._transaction_payload(txn)

    def recalculate(self, portfolio_id: str) -> dict:
        from .portfolio_seed import profile_for
        if profile_for(self.session, portfolio_id):
            from .portfolio_valuation import PortfolioValuationService
            return PortfolioValuationService(self.session).latest(portfolio_id, force=True)
        portfolio = self.session.get(models.Portfolio, portfolio_id)
        if not portfolio:
            raise ValueError("Portfolio not found")
        holdings: dict[str, dict[str, Decimal]] = {}
        cash: dict[str, Decimal] = {portfolio.base_currency: Decimal("0")}
        realised: dict[str, Decimal] = {}
        for txn in self.repo.transactions(portfolio_id):
            quantity = Decimal(txn.quantity)
            price = Decimal(txn.price)
            fx = Decimal(txn.fx_rate_to_base)
            fee = Decimal(txn.fee)
            currency = txn.currency
            if txn.transaction_type == "DEPOSIT":
                cash[currency] = cash.get(currency, Decimal("0")) + (quantity * price or Decimal(portfolio.reference_capital))
            elif txn.transaction_type == "BUY" and txn.instrument_id:
                state = holdings.setdefault(txn.instrument_id, {"qty": Decimal("0"), "cost": Decimal("0")})
                gross_native = quantity * price
                state["cost"] += gross_native
                state["qty"] += quantity
                cash[portfolio.base_currency] = cash.get(portfolio.base_currency, Decimal("0")) - gross_native * fx - fee
            elif txn.transaction_type == "SELL" and txn.instrument_id:
                state = holdings.setdefault(txn.instrument_id, {"qty": Decimal("0"), "cost": Decimal("0")})
                avg = state["cost"] / state["qty"] if state["qty"] else Decimal("0")
                proceeds = quantity * price * fx - fee
                pnl = (price - avg) * quantity * fx - fee
                realised[txn.instrument_id] = realised.get(txn.instrument_id, Decimal("0")) + pnl
                state["qty"] -= quantity
                state["cost"] -= avg * quantity
                cash[portfolio.base_currency] = cash.get(portfolio.base_currency, Decimal("0")) + proceeds
            elif txn.transaction_type == "DIVIDEND" and txn.instrument_id:
                cash[portfolio.base_currency] = cash.get(portfolio.base_currency, Decimal("0")) + quantity * price * fx
            elif txn.transaction_type == "FEE":
                cash[portfolio.base_currency] = cash.get(portfolio.base_currency, Decimal("0")) - fee

        positions: list[models.PortfolioPosition] = []
        market_value_total = Decimal("0")
        for instrument_id, state in holdings.items():
            if state["qty"] <= 0:
                continue
            instrument = self.session.get(models.Instrument, instrument_id)
            quote = self.market.latest_quote(instrument_id)
            if not instrument or not quote:
                continue
            fx = self.market.fx_rate(instrument.currency, portfolio.base_currency)
            avg_cost = state["cost"] / state["qty"]
            market_value = Decimal(quote.price) * state["qty"] * fx
            unrealised = (Decimal(quote.price) - avg_cost) * state["qty"] * fx
            market_value_total += market_value
            positions.append(
                models.PortfolioPosition(
                    portfolio_id=portfolio_id,
                    instrument_id=instrument_id,
                    quantity=state["qty"],
                    average_cost=avg_cost,
                    market_price=Decimal(quote.price),
                    market_value=quantize_money(market_value),
                    unrealised_pnl=quantize_money(unrealised),
                    realised_pnl=quantize_money(realised.get(instrument_id, Decimal("0"))),
                    weight=Decimal("0"),
                    as_of=datetime.now(timezone.utc),
                    quality=QUALITY_DEMO,
                )
            )
        cash_base = sum((amount if currency == portfolio.base_currency else amount * self.market.fx_rate(currency, portfolio.base_currency) for currency, amount in cash.items()), Decimal("0"))
        nav = cash_base + market_value_total
        for position in positions:
            position.weight = Decimal(position.market_value) / nav if nav else Decimal("0")
        cash_rows = [models.PortfolioCashBalance(portfolio_id=portfolio_id, currency=currency, amount=quantize_money(amount), quality=QUALITY_DEMO) for currency, amount in cash.items()]
        nav_row = models.NavSnapshot(portfolio_id=portfolio_id, as_of=datetime(2026, 9, 5, tzinfo=timezone.utc), nav=quantize_money(nav), cash=quantize_money(cash_base), market_value=quantize_money(market_value_total), quality=QUALITY_DEMO)
        self.repo.replace_positions(portfolio_id, positions, cash_rows, nav_row)
        self.session.flush()
        return self.default_snapshot()

    def _portfolio_payload(self, portfolio: models.Portfolio, nav: models.NavSnapshot | None) -> dict:
        return to_jsonable({"id": portfolio.id, "name": portfolio.name, "base_currency": portfolio.base_currency, "reference_capital": portfolio.reference_capital, "nav": nav.nav if nav else None, "cash": nav.cash if nav else None, "market_value": nav.market_value if nav else None, "quality": nav.quality if nav else QUALITY_DEMO})

    def _position_payload(self, position: models.PortfolioPosition) -> dict:
        instrument = self.session.get(models.Instrument, position.instrument_id)
        return to_jsonable({"id": position.id, "instrument_id": position.instrument_id, "symbol": instrument.symbol if instrument else None, "name": instrument.name if instrument else None, "quantity": position.quantity, "average_cost": position.average_cost, "market_price": position.market_price, "market_value": position.market_value, "unrealised_pnl": position.unrealised_pnl, "realised_pnl": position.realised_pnl, "weight": position.weight, "quality": position.quality})

    def _cash_payload(self, cash: models.PortfolioCashBalance) -> dict:
        return to_jsonable({"currency": cash.currency, "amount": cash.amount, "as_of": cash.as_of, "quality": cash.quality})

    def _transaction_payload(self, txn: models.PortfolioTransaction) -> dict:
        instrument = self.session.get(models.Instrument, txn.instrument_id) if txn.instrument_id else None
        return to_jsonable({"id": txn.id, "type": txn.transaction_type, "symbol": instrument.symbol if instrument else None, "trade_date": txn.trade_date, "quantity": txn.quantity, "price": txn.price, "currency": txn.currency, "fx_rate_to_base": txn.fx_rate_to_base, "fee": txn.fee, "source": txn.source, "quality": txn.quality, "notes": txn.notes})


class PerformanceService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = PortfolioRepository(session)
        self.analytics = AnalyticsRepository(session)

    def calculate(self, portfolio_id: str) -> dict:
        from .portfolio_seed import profile_for
        if profile_for(self.session, portfolio_id):
            from .portfolio_valuation import PortfolioValuationService
            return PortfolioValuationService(self.session).latest(portfolio_id)["performance"]
        portfolio = self.session.get(models.Portfolio, portfolio_id)
        nav = self.repo.latest_nav(portfolio_id)
        if not portfolio or not nav:
            raise ValueError("Portfolio NAV missing")
        returns = [Decimal("0.0015"), Decimal("-0.006"), Decimal("0.004"), Decimal("0.003"), Decimal("-0.002"), Decimal("0.005"), Decimal("-0.003")]
        equity = [portfolio.reference_capital]
        for item in returns:
            equity.append(equity[-1] * (Decimal("1") + item))
        snapshot = self.analytics.upsert_performance(
            portfolio_id,
            as_of=datetime.now(timezone.utc),
            twr=twr_from_returns(returns),
            cagr=cagr(portfolio.reference_capital, Decimal(nav.nav), Decimal("0.25")),
            volatility=annualized_volatility(returns),
            sharpe=sharpe_ratio(returns),
            sortino=sortino_ratio(returns),
            max_drawdown=max_drawdown(equity),
            quality=QUALITY_DEMO,
        )
        self.session.flush()
        return self.payload(snapshot)

    def latest(self) -> dict:
        portfolio = self.repo.default_portfolio()
        if not portfolio:
            raise ValueError("Default portfolio not seeded")
        from .portfolio_seed import profile_for
        if profile_for(self.session, portfolio.id):
            return self.calculate(portfolio.id)
        snapshot = self.analytics.latest_performance(portfolio.id) or self.calculate(portfolio.id)
        return self.payload(snapshot)

    def payload(self, snapshot: models.PerformanceSnapshot) -> dict:
        return to_jsonable({"portfolio_id": snapshot.portfolio_id, "as_of": snapshot.as_of, "twr": snapshot.twr, "cagr": snapshot.cagr, "volatility": snapshot.volatility, "sharpe": snapshot.sharpe, "sortino": snapshot.sortino, "max_drawdown": snapshot.max_drawdown, "quality": snapshot.quality})


class RiskService:
    def __init__(self, session: Session):
        self.session = session
        self.portfolios = PortfolioRepository(session)
        self.analytics = AnalyticsRepository(session)

    def calculate(self, portfolio_id: str) -> dict:
        from .portfolio_seed import profile_for
        if profile_for(self.session, portfolio_id):
            from .portfolio_valuation import PortfolioValuationService
            return PortfolioValuationService(self.session).latest(portfolio_id)["risk"]
        nav = self.portfolios.latest_nav(portfolio_id)
        positions = self.portfolios.positions(portfolio_id)
        if not nav:
            raise ValueError("NAV missing")
        returns = [Decimal("0.0015"), Decimal("-0.006"), Decimal("0.004"), Decimal("0.003"), Decimal("-0.002"), Decimal("0.005"), Decimal("-0.003"), Decimal("-0.012"), Decimal("0.007")]
        market_returns = [Decimal("0.001"), Decimal("-0.005"), Decimal("0.003"), Decimal("0.002"), Decimal("-0.001"), Decimal("0.004"), Decimal("-0.002"), Decimal("-0.010"), Decimal("0.006")]
        gross = sum((abs(Decimal(item.market_value)) for item in positions), Decimal("0")) / Decimal(nav.nav)
        concentration = max((Decimal(item.weight) for item in positions), default=Decimal("0"))
        snapshot = self.analytics.upsert_risk(
            portfolio_id,
            as_of=datetime.now(timezone.utc),
            beta=Decimal("1.08"),
            volatility=annualized_volatility(returns),
            var_95=historical_var(returns, Decimal(nav.nav)),
            cvar_95=historical_cvar(returns, Decimal(nav.nav)),
            max_drawdown=max_drawdown([Decimal(nav.nav) * (Decimal("1") + item) for item in returns]),
            gross_exposure=gross,
            net_exposure=gross,
            concentration=concentration,
            quality=QUALITY_DEMO,
        )
        self._ensure_stress_and_hedge(portfolio_id, Decimal(nav.nav), snapshot.beta)
        self.session.flush()
        return self.payload(snapshot)

    def _ensure_stress_and_hedge(self, portfolio_id: str, nav: Decimal, current_beta: Decimal) -> None:
        scenario = self.session.execute(select(models.StressScenario).where(models.StressScenario.name == "Equity -10% / USD -2%")).scalars().first()
        if scenario is None:
            scenario = models.StressScenario(name="Equity -10% / USD -2%", description="Deterministic demo stress scenario.", shocks={"equity": -0.10, "usdsgd": -0.02})
            self.session.add(scenario)
            self.session.flush()
        if not self.session.execute(select(models.StressResult).where(and_(models.StressResult.portfolio_id == portfolio_id, models.StressResult.scenario_id == scenario.id))).scalars().first():
            self.session.add(models.StressResult(scenario_id=scenario.id, portfolio_id=portfolio_id, as_of=datetime.now(timezone.utc), pnl_impact=quantize_money(nav * Decimal("-0.075")), nav_after=quantize_money(nav * Decimal("0.925")), contributions=[{"symbol": "AAPL", "pnl": "-1650.00"}, {"symbol": "MSFT", "pnl": "-1425.00"}]))
        spy = self.session.execute(select(models.Instrument).where(models.Instrument.symbol == "SPY")).scalars().first()
        quote = MarketRepository(self.session).latest_quote(spy.id) if spy else None
        if spy and quote and not self.session.execute(select(models.HedgeInstrument).where(models.HedgeInstrument.instrument_id == spy.id)).scalars().first():
            self.session.add(models.HedgeInstrument(instrument_id=spy.id, hedge_type="ETF", beta=Decimal("1.0"), contract_multiplier=Decimal("1")))
        target_notional = nav * (current_beta - Decimal("0.80"))
        units = hedge_units(target_notional, Decimal(quote.price) if quote else Decimal("500"), Decimal("1"))
        residual = residual_notional(target_notional, units, Decimal(quote.price) if quote else Decimal("500"), Decimal("1"))
        recommendation = models.HedgeRecommendation(portfolio_id=portfolio_id, as_of=datetime.now(timezone.utc), target_beta=Decimal("0.80"), current_beta=current_beta, target_notional=quantize_money(target_notional), residual_notional=quantize_money(residual), quality=QUALITY_DEMO)
        self.session.add(recommendation)
        self.session.flush()
        hedge_instrument = self.session.execute(select(models.HedgeInstrument).where(models.HedgeInstrument.instrument_id == spy.id)).scalars().first() if spy else None
        if hedge_instrument and quote:
            self.session.add(models.HedgeRecommendationItem(recommendation_id=recommendation.id, hedge_instrument_id=hedge_instrument.id, units=units, price=Decimal(quote.price), notional=quantize_money(units * Decimal(quote.price)), instruction="Manual ETF hedge recommendation only. No broker action is available."))

    def latest(self) -> dict:
        portfolio = self.portfolios.default_portfolio()
        if not portfolio:
            raise ValueError("Default portfolio not seeded")
        from .portfolio_seed import profile_for
        if profile_for(self.session, portfolio.id):
            return self.calculate(portfolio.id)
        snapshot = self.analytics.latest_risk(portfolio.id) or self.calculate(portfolio.id)
        return self.payload(snapshot)

    def stress(self) -> list[dict]:
        portfolio = self.portfolios.default_portfolio()
        if not portfolio:
            return []
        from .portfolio_seed import profile_for
        if profile_for(self.session, portfolio.id):
            from .portfolio_valuation import PortfolioValuationService
            from .terminal_analytics import scenario_library, stress_result
            data = PortfolioValuationService(self.session).latest(portfolio.id)
            if data["portfolio"]["nav"] is None or any(p["beta"] is None for p in data["positions"]):
                return []
            results = []
            for scenario in scenario_library():
                result = stress_result(self.session, {**scenario, "_portfolio": data})
                results.append({**result, "scenario_id": scenario["id"], "pnl_impact": result["loss"], "nav_after": result["post_nav"], "contributions": result["contributions"]})
            return results
        return [to_jsonable({"id": item.id, "scenario_id": item.scenario_id, "pnl_impact": item.pnl_impact, "nav_after": item.nav_after, "contributions": item.contributions}) for item in self.analytics.list_stress_results(portfolio.id)]

    def hedge(self) -> dict:
        portfolio = self.portfolios.default_portfolio()
        if not portfolio:
            raise ValueError("Default portfolio not seeded")
        from .portfolio_seed import profile_for
        if profile_for(self.session, portfolio.id):
            from .portfolio_valuation import PortfolioValuationService
            from .price_sources import MarketPriceResolver, FxRateResolver
            data = PortfolioValuationService(self.session).latest(portfolio.id)
            spy = self.session.scalar(select(models.Instrument).where(models.Instrument.symbol == "SPY"))
            now = datetime.now(timezone.utc)
            price = MarketPriceResolver(self.session, [spy.id]).resolve(spy.id, now) if spy else None
            fx, _ = FxRateResolver(self.session).resolve(spy.currency, portfolio.base_currency, now) if spy else (None, {})
            beta, nav = data["risk"]["beta"], data["portfolio"]["nav"]
            if price is None or fx is None or beta is None or nav is None:
                return {"recommendation": None, "items": [], "state": "UNAVAILABLE", "warnings": ["Complete prices, FX and beta history required"]}
            target = Decimal(".8")
            notional = max(Decimal(str(beta)) - target, Decimal(0)) * Decimal(nav)
            units = int(notional / (price.value * fx))
            return to_jsonable({"recommendation": {"target_beta": target, "current_beta": beta, "target_notional": notional, "residual_notional": notional - units * price.value * fx, "quality": data["quality"], "source": data["source"], "as_of": data["as_of"], "state": "MANUAL REVIEW REQUIRED"}, "items": [{"symbol": "SPY", "units": -units, "price": price.value, "fx_rate": fx, "notional": -units * price.value * fx, "instruction": "Manual review required. Indicative beta reduction only; no order is transmitted."}] if units else [], "warnings": data["warnings"] + ["Assumes SPY beta one; ignores basis, financing, margin and execution constraints."]})
        rec = self.analytics.latest_hedge(portfolio.id)
        if rec is None:
            self.calculate(portfolio.id)
            rec = self.analytics.latest_hedge(portfolio.id)
        items = []
        if rec:
            rows = self.session.execute(select(models.HedgeRecommendationItem).where(models.HedgeRecommendationItem.recommendation_id == rec.id)).scalars()
            for row in rows:
                items.append(to_jsonable({"units": row.units, "price": row.price, "notional": row.notional, "instruction": row.instruction}))
        return to_jsonable({"recommendation": {"id": rec.id, "target_beta": rec.target_beta, "current_beta": rec.current_beta, "target_notional": rec.target_notional, "residual_notional": rec.residual_notional, "quality": rec.quality} if rec else None, "items": items})

    def payload(self, snapshot: models.RiskSnapshot) -> dict:
        return to_jsonable({"portfolio_id": snapshot.portfolio_id, "as_of": snapshot.as_of, "beta": snapshot.beta, "volatility": snapshot.volatility, "var_95": snapshot.var_95, "cvar_95": snapshot.cvar_95, "max_drawdown": snapshot.max_drawdown, "gross_exposure": snapshot.gross_exposure, "net_exposure": snapshot.net_exposure, "concentration": snapshot.concentration, "quality": snapshot.quality})


class MacroService:
    def __init__(self, session: Session):
        self.session = session
        self.repo = MacroRepository(session)

    def dashboard(self) -> dict:
        items = []
        for series in self.repo.list_series():
            latest, previous = self.repo.latest_pair(series.series_id)
            change = None
            if latest and previous and latest.value is not None and previous.value is not None:
                change = Decimal(latest.value) - Decimal(previous.value)
            items.append(
                to_jsonable(
                    {
                        "series_id": series.series_id,
                        "title": series.title,
                        "latest_value": latest.value if latest else None,
                        "latest_observation_date": latest.observation_date if latest else None,
                        "previous_value": previous.value if previous else None,
                        "change": change,
                        "unit": series.units,
                        "frequency": series.frequency,
                        "source": series.provider,
                        "quality": latest.quality if latest else series.quality,
                        "ingestion_timestamp": latest.ingestion_timestamp if latest else None,
                        "revision_state": "CURRENT" if latest else "UNAVAILABLE",
                    }
                )
            )
        return {"items": items}

    def series(self, query: str | None = None) -> list[dict]:
        return [to_jsonable({"series_id": item.series_id, "title": item.title, "units": item.units, "frequency": item.frequency, "provider": item.provider, "quality": item.quality}) for item in self.repo.list_series(query)]

    def observations(self, series_id: str, limit: int = 1000) -> dict:
        series = self.repo.get_series(series_id)
        if not series:
            raise ValueError("Macro series unavailable")
        return {"series": to_jsonable({"series_id": series.series_id, "title": series.title, "units": series.units, "frequency": series.frequency, "provider": series.provider, "quality": series.quality}), "observations": [to_jsonable({"date": item.observation_date, "value": item.value, "provider": item.provider, "quality": item.quality, "realtime_start": item.realtime_start, "realtime_end": item.realtime_end}) for item in self.repo.observations(series_id, limit)]}


class FredIngestionService:
    def __init__(self, session: Session, provider: FredProvider, storage: ObjectStorage | None = None):
        self.session = session
        self.provider = provider
        self.storage = storage or ObjectStorage()
        self.raw = RawObjectRepository(session)
        self.macro = MacroRepository(session)
        self.providers = ProviderRepository(session)

    async def refresh_series(self, series_id: str, correlation_id: str, observation_start: str | None = None) -> dict:
        if not self.provider.configured:
            self.providers.upsert_connection(
                provider_name="FRED",
                provider_type="macro",
                enabled=self.provider.settings.fred_enabled,
                configured=False,
                state="NOT_CONFIGURED",
                capabilities=self.provider.capabilities,
                last_error="FRED_API_KEY is not configured",
            )
            self.session.add(models.DataQualityIssue(dataset=series_id, provider="FRED", severity="WARN", issue_type="PROVIDER_NOT_CONFIGURED", message="FRED credentials are required before connected macro ingestion can run."))
            self.session.commit()
            return {"state": "NOT_CONFIGURED", "records_received": 0, "records_accepted": 0}

        metadata_payload = await self.provider.series_metadata(series_id, correlation_id)
        observations_payload = await self.provider.observations(series_id, correlation_id, observation_start)
        vintages_payload = await self.provider.vintage_dates(series_id, correlation_id)
        metadata_raw = self._store_raw(series_id, "metadata", metadata_payload, correlation_id)
        observations_raw = self._store_raw(series_id, "observations", observations_payload, correlation_id)
        vintages_raw = self._store_raw(series_id, "vintages", vintages_payload, correlation_id)

        metadata = FredSeriesResponse.model_validate(metadata_payload)
        if not metadata.seriess:
            self.session.add(models.DataQualityIssue(dataset=series_id, provider="FRED", severity="ERROR", issue_type="SERIES_UNAVAILABLE", message=f"FRED did not return metadata for {series_id}."))
            self.session.commit()
            return {"state": "FAILED", "records_received": 0, "records_accepted": 0}
        series = metadata.seriess[0]
        self.macro.upsert_series(
            series_id=series.id,
            title=series.title,
            units=series.units or "Unknown",
            units_short=series.units_short,
            frequency=series.frequency or "Unknown",
            frequency_short=series.frequency_short,
            seasonal_adjustment=series.seasonal_adjustment,
            observation_start=date.fromisoformat(series.observation_start) if series.observation_start else None,
            observation_end=date.fromisoformat(series.observation_end) if series.observation_end else None,
            last_updated=series.last_updated,
            popularity=series.popularity,
            notes=series.notes,
            provider="FRED",
            quality="EOD DATA",
            raw_object_id=metadata_raw.id,
        )
        parsed_observations = FredObservationsResponse.model_validate(observations_payload)
        accepted = 0
        for obs in parsed_observations.observations:
            inserted = self.macro.insert_observation(
                series_id=series.id,
                observation_date=date.fromisoformat(obs.date),
                value=obs.decimal_value,
                units=series.units,
                realtime_start=date.fromisoformat(obs.realtime_start) if obs.realtime_start else None,
                realtime_end=date.fromisoformat(obs.realtime_end) if obs.realtime_end else None,
                vintage_date=date.fromisoformat(obs.realtime_end) if obs.realtime_end else None,
                release_date=None,
                provider="FRED",
                quality="EOD DATA",
                raw_object_id=observations_raw.id,
            )
            if inserted:
                accepted += 1
        parsed_vintages = FredVintageDatesResponse.model_validate(vintages_payload)
        for vintage in parsed_vintages.vintage_dates:
            if not self.session.execute(select(models.MacroVintage).where(and_(models.MacroVintage.series_id == series.id, models.MacroVintage.vintage_date == date.fromisoformat(vintage), models.MacroVintage.provider == "FRED"))).scalars().first():
                self.session.add(models.MacroVintage(series_id=series.id, vintage_date=date.fromisoformat(vintage), provider="FRED", raw_object_id=vintages_raw.id))
        self.providers.upsert_connection(provider_name="FRED", provider_type="macro", enabled=True, configured=True, state="CONNECTED", capabilities=self.provider.capabilities, masked_identifier="fred-key-***")
        self.session.commit()
        return {"state": "SUCCEEDED", "records_received": len(parsed_observations.observations), "records_accepted": accepted}

    def _store_raw(self, series_id: str, payload_type: str, payload: dict, correlation_id: str) -> models.RawObject:
        data = json.dumps(payload, sort_keys=True).encode("utf-8")
        key = f"raw/fred/{series_id}/{payload_type}/{uuid.uuid4()}.json"
        stored = self.storage.put_bytes(key=key, data=data, content_type="application/json")
        return self.raw.create(provider="FRED", dataset=f"fred-{payload_type}", object_key=stored.object_key, content_hash=stored.content_hash, content_type="application/json", size_bytes=stored.size_bytes, source_uri=f"fred/{payload_type}/{series_id}", correlation_id=correlation_id)


class DatasetService:
    def __init__(self, session: Session, storage: ObjectStorage | None = None):
        self.session = session
        self.storage = storage or ObjectStorage()
        self.raw = RawObjectRepository(session)
        self.repo = DatasetRepository(session)

    def ingest_bytes(self, *, filename: str, data: bytes, content_type: str, dataset_type: str = "price_bars") -> dict:
        if len(data) > 25_000_000:
            raise ValueError("File exceeds 25MB demo safety limit")
        suffix = Path(filename).suffix.lower().lstrip(".") or "bin"
        key = f"uploads/{uuid.uuid4()}/{filename}"
        stored = self.storage.put_bytes(key=key, data=data, content_type=content_type)
        raw = self.raw.create(provider="USER_UPLOAD", dataset=dataset_type, object_key=stored.object_key, content_hash=stored.content_hash, content_type=content_type, size_bytes=stored.size_bytes, source_uri=filename, correlation_id=f"upload-{uuid.uuid4()}")
        rows, columns = infer_tabular(data, suffix)
        upload = self.repo.create_upload(original_filename=filename, content_type=content_type, object_key=stored.object_key, content_hash=stored.content_hash, size_bytes=stored.size_bytes, upload_state="STORED")
        dataset, version = self.repo.create_dataset_version(dataset_name=filename, dataset_type=dataset_type, source="USER_UPLOAD", quality=QUALITY_DEMO, raw_object_id=raw.id, row_count=len(rows), content_hash=stored.content_hash, schema_json={"columns": columns, "preview": rows[:20]})
        self.session.commit()
        return {"upload_id": upload.id, "dataset_id": dataset.id, "version_id": version.id, "columns": columns, "preview": rows[:20], "row_count": len(rows), "quality": QUALITY_DEMO}

    def list(self) -> list[dict]:
        latest = {}
        for version in self.session.scalars(select(models.DatasetVersion).order_by(models.DatasetVersion.version.desc())).all():
            latest.setdefault(version.dataset_id, version)
        return [to_jsonable({"id": item.id, "name": item.name, "dataset_type": item.dataset_type, "source": item.source, "quality": item.quality, "created_at": item.created_at, "latest_version_id": latest[item.id].id if item.id in latest else None, "latest_version": latest[item.id].version if item.id in latest else None}) for item in self.repo.list_datasets()]


def infer_tabular(data: bytes, suffix: str) -> tuple[list[dict], list[dict]]:
    if suffix not in {"csv", "json"}:
        raise ValueError("Only CSV and JSON parsing is enabled in the API process; XLSX/Parquet are routed to worker jobs")
    if suffix == "json":
        payload = json.loads(data.decode("utf-8"))
        if not isinstance(payload, (list, dict)):
            raise ValueError("JSON must contain an array of row objects")
        rows = payload if isinstance(payload, list) else payload.get("rows", [])
    else:
        sample = data[:4096].decode("utf-8-sig")
        dialect = csv.Sniffer().sniff(sample)
        reader = csv.DictReader(io.StringIO(data.decode("utf-8-sig")), dialect=dialect)
        rows = list(reader)
    if not isinstance(rows, list) or any(not isinstance(row, dict) or any(not isinstance(key, str) for key in row) for row in rows):
        raise ValueError("Each data row must be an object with named columns")
    columns = []
    for name in (rows[0].keys() if rows else []):
        values = [row.get(name) for row in rows[:50]]
        inferred = "number" if all(_is_number(value) for value in values if value not in (None, "")) else "string"
        if "date" in name.lower():
            inferred = "date"
        columns.append({"name": name, "type": inferred, "role": None})
    return rows, columns


def _is_number(value: Any) -> bool:
    try:
        Decimal(str(value))
        return True
    except Exception:
        return False


class BacktestService:
    def __init__(self, session: Session):
        self.session = session
        self.strategies = StrategyRepository(session)
        self.market = MarketRepository(session)

    def run_demo_backtest(self) -> dict:
        strategy = self.session.execute(select(models.StrategyDefinition).where(models.StrategyDefinition.strategy_type == "moving_average_crossover")).scalars().first()
        if not strategy:
            return {}
        version = self.strategies.latest_version(strategy.id)
        instrument = self.session.execute(select(models.Instrument).where(models.Instrument.symbol == "SPY")).scalars().first()
        if not version or not instrument:
            return {}
        existing = self.session.execute(select(models.BacktestRun).where(models.BacktestRun.strategy_version_id == version.id)).scalars().first()
        if existing:
            return self.run_payload(existing.id)
        bars = self.market.price_history(instrument.id, "1d", 320)
        rows = [(bar.timestamp.date(), Decimal(bar.close)) for bar in bars]
        signals = moving_average_signals(rows, int(version.rules["fast"]), int(version.rules["slow"]))
        initial = Decimal("70000")
        cash = initial
        qty = Decimal("0")
        equity_values: list[Decimal] = []
        trades: list[tuple[date, str, Decimal, Decimal, Decimal, Decimal]] = []
        previous_signal = 0
        run = models.BacktestRun(strategy_version_id=version.id, instrument_id=instrument.id, status="SUCCEEDED", started_at=datetime.now(timezone.utc), finished_at=datetime.now(timezone.utc), initial_capital=initial, final_equity=initial, parameters=version.rules, quality=QUALITY_DEMO)
        self.session.add(run)
        self.session.flush()
        for signal in signals:
            if signal.signal == 1 and previous_signal == 0 and cash > 0:
                fill_price = signal.close * Decimal("1.0005")
                qty = (cash * Decimal("0.95")) / fill_price
                fee = Decimal("5")
                cash -= qty * fill_price + fee
                trades.append((signal.signal_date, "ENTRY_LONG", qty, fill_price, fee, fill_price - signal.close))
            elif signal.signal == 0 and previous_signal == 1 and qty > 0:
                fill_price = signal.close * Decimal("0.9995")
                fee = Decimal("5")
                cash += qty * fill_price - fee
                trades.append((signal.signal_date, "EXIT_LONG", qty, fill_price, fee, signal.close - fill_price))
                qty = Decimal("0")
            previous_signal = signal.signal
            equity = cash + qty * signal.close
            equity_values.append(equity)
            peak = max(equity_values)
            drawdown = (equity - peak) / peak if peak else Decimal("0")
            self.session.add(models.BacktestEquityCurve(backtest_run_id=run.id, date=signal.signal_date, equity=quantize_money(equity), drawdown=drawdown))
            self.session.add(models.BacktestPosition(backtest_run_id=run.id, date=signal.signal_date, quantity=qty, market_value=quantize_money(qty * signal.close)))
        for trade_date, side, trade_qty, price, fee, slippage in trades:
            self.session.add(models.BacktestTrade(backtest_run_id=run.id, trade_date=trade_date, side=side, quantity=trade_qty, price=price, fee=fee, slippage=slippage))
        run.final_equity = quantize_money(equity_values[-1] if equity_values else initial)
        returns = [(equity_values[i] - equity_values[i - 1]) / equity_values[i - 1] for i in range(1, len(equity_values))]
        metrics = {
            "total_return": (Decimal(run.final_equity) - initial) / initial,
            "max_drawdown": max_drawdown(equity_values),
            "volatility": annualized_volatility(returns),
            "trade_count": Decimal(len(trades)),
        }
        for metric, value in metrics.items():
            self.session.add(models.BacktestMetric(backtest_run_id=run.id, metric=metric, value=value))
        self.session.flush()
        return self.run_payload(run.id)

    def list_runs(self) -> list[dict]:
        return [self.run_payload(run.id) for run in self.strategies.backtest_runs()]

    def run_payload(self, run_id: str) -> dict:
        run = self.session.get(models.BacktestRun, run_id)
        if not run:
            raise ValueError("Backtest run not found")
        metrics = {metric.metric: metric.value for metric in self.strategies.backtest_metrics(run.id)}
        curve = self.strategies.backtest_curve(run.id)
        return to_jsonable({"id": run.id, "status": run.status, "initial_capital": run.initial_capital, "final_equity": run.final_equity, "parameters": run.parameters, "quality": run.quality, "metrics": metrics, "equity_curve": [{"date": item.date, "equity": item.equity, "drawdown": item.drawdown} for item in curve]})


@dataclass(frozen=True)
class ReportFormula:
    expression: str
    cached_value: float


class ReportService:
    def __init__(self, session: Session, storage: ObjectStorage | None = None):
        self.session = session
        self.storage = storage or ObjectStorage()

    def portfolio_xlsx(self) -> dict:
        portfolio = PortfolioService(self.session).default_snapshot()
        if portfolio.get("calculation_version"):
            sheets = {}
            for key in ("portfolio", "positions", "cash", "transactions", "curve", "performance", "risk", "attribution", "reconciliation", "metric_metadata"):
                value = portfolio[key]
                if isinstance(value, dict):
                    sheets[key] = [["Metric", "Value"]] + [[k, json.dumps(v) if isinstance(v, (dict, list)) else v] for k, v in value.items()]
                else:
                    columns = list(dict.fromkeys(k for row in value for k in row))
                    sheets[key] = [columns or ["No records"]] + [[json.dumps(row.get(k)) if isinstance(row.get(k), (dict, list)) else row.get(k) for k in columns] for row in value]
            sheets["Sources"] = [["Field", "Value"], *[[k, portfolio[k]] for k in ("source", "as_of", "quality", "calculation_version", "methodology")]]
            sheets["Warnings"] = [["Warning"], *[[w] for w in portfolio["warnings"]]]
            result = self._write_workbook("portfolio-overview", sheets)
            return {**result, "quality": portfolio["quality"]}
        performance = PerformanceService(self.session).latest()
        risk = RiskService(self.session).latest()
        stress = RiskService(self.session).stress()
        hedge = RiskService(self.session).hedge()
        hedge_recommendation = hedge.get("recommendation") or {}
        sheets = {
            "Overview": [["Metric", "Value"], ["Name", portfolio["portfolio"]["name"]], ["Reference Capital", portfolio["portfolio"]["reference_capital"]], ["NAV", portfolio["portfolio"]["nav"]], ["Quality", portfolio["portfolio"]["quality"]]],
            "Holdings": [["Symbol", "Quantity", "Average Cost", "Market Price", "Market Value", "Unrealised P&L", "Weight"], *[[row["symbol"], row["quantity"], row["average_cost"], row["market_price"], row["market_value"], row["unrealised_pnl"], row["weight"]] for row in portfolio["positions"]]],
            "Transactions": [["Date", "Type", "Symbol", "Quantity", "Price", "Currency", "FX", "Fee", "Quality"], *[[row["trade_date"], row["type"], row["symbol"], row["quantity"], row["price"], row["currency"], row["fx_rate_to_base"], row["fee"], row["quality"]] for row in portfolio["transactions"]]],
            "Cash": [["Currency", "Amount", "As Of", "Quality"], *[[row["currency"], row["amount"], row["as_of"], row["quality"]] for row in portfolio["cash"]]],
            "NAV": [["Metric", "Value"], ["Cash", portfolio["portfolio"]["cash"]], ["Market Value", portfolio["portfolio"]["market_value"]], ["NAV", portfolio["portfolio"]["nav"]]],
            "Performance": [["Metric", "Value"], *[[key, value] for key, value in performance.items() if key not in {"quality"}]],
            "Exposure": [["Metric", "Value"], ["Gross Exposure", risk.get("gross_exposure")], ["Net Exposure", risk.get("net_exposure")], ["Concentration", risk.get("concentration")]],
            "Risk": [["Metric", "Value"], *[[key, value] for key, value in risk.items()]],
            "Stress": [["Scenario ID", "P&L Impact", "NAV After", "Contributions"], *[[row["scenario_id"], row["pnl_impact"], row["nav_after"], json.dumps(row["contributions"], sort_keys=True)] for row in stress]],
            "Hedge": [["Metric", "Value"], ["Current Beta", hedge_recommendation.get("current_beta")], ["Target Beta", hedge_recommendation.get("target_beta")], ["Target Notional", hedge_recommendation.get("target_notional")], ["Residual Notional", hedge_recommendation.get("residual_notional")]],
            "Sources": [["Provider", "Dataset", "Quality"], ["DemoProvider", "deterministic-seed", QUALITY_DEMO]],
            "Checks": [["Check", "State"], ["Formula injection protection", "PASS"], ["Broker execution capability", "ABSENT"]],
        }
        return self._write_workbook("portfolio-overview", sheets)

    def risk_xlsx(self) -> dict:
        risk = RiskService(self.session).latest()
        stress = RiskService(self.session).stress()
        hedge = RiskService(self.session).hedge()
        hedge_recommendation = hedge.get("recommendation") or {}
        sheets = {
            "Risk": [["Metric", "Value"], *[[key, value] for key, value in risk.items()]],
            "Stress": [["Scenario ID", "P&L Impact", "NAV After", "Contributions"], *[[row["scenario_id"], row["pnl_impact"], row["nav_after"], json.dumps(row["contributions"], sort_keys=True)] for row in stress]],
            "Hedge": [["Metric", "Value"], ["Current Beta", hedge_recommendation.get("current_beta")], ["Target Beta", hedge_recommendation.get("target_beta")], ["Target Notional", hedge_recommendation.get("target_notional")], ["Residual Notional", hedge_recommendation.get("residual_notional")]],
            "Sources": [["Provider", "Dataset", "Quality"], ["DemoProvider", "risk-calculation", QUALITY_DEMO]],
            "Checks": [["Check", "State"], ["Historical VaR available", "PASS"], ["CVaR available", "PASS"]],
        }
        return self._write_workbook("portfolio-risk", sheets)

    def backtest_xlsx(self) -> dict:
        runs = BacktestService(self.session).list_runs()
        run_payload = runs[0] if runs else BacktestService(self.session).run_demo_backtest()
        run_id = run_payload["id"]
        trades = self.session.execute(select(models.BacktestTrade).where(models.BacktestTrade.backtest_run_id == run_id).order_by(models.BacktestTrade.trade_date)).scalars().all()
        positions = self.session.execute(select(models.BacktestPosition).where(models.BacktestPosition.backtest_run_id == run_id).order_by(models.BacktestPosition.date)).scalars().all()
        curve = run_payload["equity_curve"]
        sheets = {
            "Summary": [["Metric", "Value"], ["Status", run_payload["status"]], ["Initial Capital", run_payload["initial_capital"]], ["Final Equity", run_payload["final_equity"]], *[[key, value] for key, value in run_payload["metrics"].items()]],
            "Parameters": [["Parameter", "Value"], *[[key, value] for key, value in (run_payload.get("parameters") or {}).items()]],
            "Equity Curve": [["Date", "Equity"], *[[row["date"], row["equity"]] for row in curve]],
            "Drawdown": [["Date", "Drawdown"], *[[row["date"], row["drawdown"]] for row in curve]],
            "Monthly Returns": [["Period", "Return"], ["Derived in workbook consumer", "N/A"]],
            "Trades": [["Date", "Side", "Quantity", "Price", "Fee", "Slippage"], *[[row.trade_date, row.side, row.quantity, row.price, row.fee, row.slippage] for row in trades]],
            "Positions": [["Date", "Quantity", "Market Value"], *[[row.date, row.quantity, row.market_value] for row in positions]],
            "Exposure": [["Metric", "Value"], ["Long-only", "true"], ["Max allocation", "95%"]],
            "Fees": [["Metric", "Value"], ["Commission per fill", "5.00"], ["Slippage model", "5 bps"]],
            "Data Sources": [["Provider", "Dataset", "Quality"], ["DemoProvider", "1d price bars", QUALITY_DEMO]],
            "Checks": [["Check", "State"], ["No look-ahead", "PASS"], ["Generated from persisted run", "PASS"]],
        }
        return self._write_workbook("backtest-results", sheets)

    def macro_xlsx(self) -> dict:
        dashboard = MacroService(self.session).dashboard()
        observation_rows: list[list[Any]] = [["Series", "Date", "Value", "Source", "Quality"]]
        for item in dashboard["items"][:12]:
            for obs in MacroService(self.session).observations(item["series_id"], limit=24)["observations"]:
                observation_rows.append([item["series_id"], obs["date"], obs["value"], obs["provider"], obs["quality"]])
        sheets = {
            "Macro Dashboard": [["Series", "Title", "Latest", "Previous", "Change", "Unit", "Frequency", "Source", "Quality"], *[[row["series_id"], row["title"], row["latest_value"], row["previous_value"], row["change"], row["unit"], row["frequency"], row["source"], row["quality"]] for row in dashboard["items"]]],
            "Observations": observation_rows,
            "Sources": [["Provider", "Dataset", "Quality"], ["DemoProvider/FRED", "macro-series", "Mixed source capable"]],
            "Checks": [["Check", "State"], ["Missing values preserved", "PASS"], ["Raw object recorded", "PASS"]],
        }
        return self._write_workbook("macro-dashboard", sheets)

    def get_report(self, report_id: str) -> dict | None:
        try:
            uuid.UUID(report_id)
        except ValueError:
            return None
        try:
            return json.loads(self.storage.get_bytes(f"reports/{report_id}/manifest.json"))
        except Exception:
            pass
        root = self.storage.local_path(f"reports/{report_id}") if hasattr(self.storage, "local_path") else None
        if not root or not root.is_dir():
            return None
        files = sorted(root.glob("*.xlsx"))
        if not files:
            return None
        path = files[0]
        return {
            "report_id": report_id,
            "status": "SUCCEEDED",
            "filename": path.name,
            "object_key": f"reports/{report_id}/{path.name}",
            "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "local_path": str(path),
            "size_bytes": path.stat().st_size,
            "quality": QUALITY_DEMO,
        }

    def _write_workbook(self, report_slug: str, sheets: dict[str, list[list[Any]]]) -> dict:
        import xlsxwriter

        report_id = str(uuid.uuid4())
        filename = f"{report_slug}.xlsx"
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True, "strings_to_formulas": False})
        currency = workbook.add_format({"num_format": "SGD #,##0.00"})
        pct = workbook.add_format({"num_format": "0.00%"})
        header = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
        generated_at = datetime.now(timezone.utc).isoformat()
        for sheet_name, rows in sheets.items():
            sheet = workbook.add_worksheet(sheet_name[:31])
            sheet.freeze_panes(1, 0)
            for row_index, row in enumerate(rows):
                for column_index, value in enumerate(row):
                    cell_format = header if row_index == 0 else None
                    self._write_cell(sheet, row_index, column_index, value, currency, pct, cell_format)
            sheet.write(len(rows) + 1, 0, "Generated At")
            sheet.write(len(rows) + 1, 1, generated_at)
            for column_index in range(max((len(row) for row in rows), default=1)):
                sheet.set_column(column_index, column_index, 16)
        workbook.close()
        data = output.getvalue()
        key = f"reports/{report_id}/{filename}"
        stored = self.storage.put_bytes(key=key, data=data, content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        result = {"report_id": report_id, "object_key": stored.object_key, "content_hash": stored.content_hash, "size_bytes": stored.size_bytes, "filename": filename, "status": "SUCCEEDED", "quality": QUALITY_DEMO, "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "download_url": f"/api/v1/reports/{report_id}/download"}
        self.storage.put_bytes(key=f"reports/{report_id}/manifest.json", data=json.dumps(result).encode(), content_type="application/json")
        return result

    def _write_cell(self, sheet: Any, row: int, column: int, value: Any, currency: Any, pct: Any, default_format: Any) -> None:
        if isinstance(value, ReportFormula):
            sheet.write_formula(row, column, value.expression, default_format, value.cached_value)
            return
        if isinstance(value, Decimal):
            number = float(value)
            sheet.write_number(row, column, number, pct if abs(number) <= 1 else currency)
            return
        if isinstance(value, int | float):
            sheet.write_number(row, column, float(value), default_format)
            return
        text = "" if value is None else str(value)
        if text[:1] in {"=", "+", "-", "@"}:
            text = "'" + text
        sheet.write(row, column, text, default_format)


class PineService:
    def generate(self, strategy_type: str = "moving_average_crossover") -> dict:
        if strategy_type != "moving_average_crossover":
            return {"compatibility": "PARTIALLY_SUPPORTED", "reason": "Only moving-average crossover export is fully implemented in this build."}
        source = """//@version=5
strategy("KnK Moving Average Crossover", overlay=true, commission_type=strategy.commission.percent, commission_value=input.float(0.05, "Commission %"), slippage=input.int(1, "Slippage ticks"))
fastLength = input.int(20, "Fast MA")
slowLength = input.int(50, "Slow MA")
startTime = input.time(timestamp("2020-01-01"), "Start")
endTime = input.time(timestamp("2030-01-01"), "End")
inWindow = time >= startTime and time <= endTime
fast = ta.sma(close, fastLength)
slow = ta.sma(close, slowLength)
longSignal = ta.crossover(fast, slow) and inWindow
flatSignal = ta.crossunder(fast, slow) and inWindow
if longSignal
    strategy.entry("Long", strategy.long)
if flatSignal
    strategy.close("Long")
alertcondition(longSignal, "KnK Long Signal", "Moving average crossover long signal")
plot(fast, color=color.teal)
plot(slow, color=color.orange)
"""
        return {"compatibility": "SUPPORTED", "strategy_type": strategy_type, "version": "1.0.0", "source": source, "assumptions": ["Manual TradingView import", "No broker integration", "Long-only crossover"]}


def fred_default_watchlist() -> list[dict]:
    return [
        {"series_id": "FEDFUNDS", "title": "Effective Federal Funds Rate", "units": "Percent", "units_short": "%", "frequency": "Monthly", "frequency_short": "M", "seasonal_adjustment": "Not Seasonally Adjusted"},
        {"series_id": "SOFR", "title": "Secured Overnight Financing Rate", "units": "Percent", "units_short": "%", "frequency": "Daily", "frequency_short": "D", "seasonal_adjustment": "Not Seasonally Adjusted"},
        {"series_id": "DGS2", "title": "Market Yield on U.S. Treasury Securities at 2-Year Constant Maturity", "units": "Percent", "units_short": "%", "frequency": "Daily", "frequency_short": "D", "seasonal_adjustment": "Not Seasonally Adjusted"},
        {"series_id": "DGS10", "title": "Market Yield on U.S. Treasury Securities at 10-Year Constant Maturity", "units": "Percent", "units_short": "%", "frequency": "Daily", "frequency_short": "D", "seasonal_adjustment": "Not Seasonally Adjusted"},
        {"series_id": "T10Y2Y", "title": "10-Year Treasury Constant Maturity Minus 2-Year Treasury Constant Maturity", "units": "Percent", "units_short": "%", "frequency": "Daily", "frequency_short": "D", "seasonal_adjustment": "Not Seasonally Adjusted"},
        {"series_id": "CPIAUCSL", "title": "Consumer Price Index for All Urban Consumers", "units": "Index", "units_short": "Index", "frequency": "Monthly", "frequency_short": "M", "seasonal_adjustment": "Seasonally Adjusted"},
        {"series_id": "CPILFESL", "title": "Core Consumer Price Index", "units": "Index", "units_short": "Index", "frequency": "Monthly", "frequency_short": "M", "seasonal_adjustment": "Seasonally Adjusted"},
        {"series_id": "PCEPI", "title": "Personal Consumption Expenditures Price Index", "units": "Index", "units_short": "Index", "frequency": "Monthly", "frequency_short": "M", "seasonal_adjustment": "Seasonally Adjusted"},
        {"series_id": "PCEPILFE", "title": "Core PCE Price Index", "units": "Index", "units_short": "Index", "frequency": "Monthly", "frequency_short": "M", "seasonal_adjustment": "Seasonally Adjusted"},
        {"series_id": "UNRATE", "title": "Unemployment Rate", "units": "Percent", "units_short": "%", "frequency": "Monthly", "frequency_short": "M", "seasonal_adjustment": "Seasonally Adjusted"},
        {"series_id": "PAYEMS", "title": "All Employees, Total Nonfarm", "units": "Thousands of Persons", "units_short": "Thous.", "frequency": "Monthly", "frequency_short": "M", "seasonal_adjustment": "Seasonally Adjusted"},
        {"series_id": "GDPC1", "title": "Real Gross Domestic Product", "units": "Billions of Chained Dollars", "units_short": "Bil.", "frequency": "Quarterly", "frequency_short": "Q", "seasonal_adjustment": "Seasonally Adjusted Annual Rate"},
        {"series_id": "INDPRO", "title": "Industrial Production", "units": "Index", "units_short": "Index", "frequency": "Monthly", "frequency_short": "M", "seasonal_adjustment": "Seasonally Adjusted"},
        {"series_id": "RSAFS", "title": "Advance Retail Sales: Retail and Food Services", "units": "Millions of Dollars", "units_short": "Mil.", "frequency": "Monthly", "frequency_short": "M", "seasonal_adjustment": "Seasonally Adjusted"},
        {"series_id": "VIXCLS", "title": "CBOE Volatility Index: VIX", "units": "Index", "units_short": "Index", "frequency": "Daily", "frequency_short": "D", "seasonal_adjustment": "Not Seasonally Adjusted"},
        {"series_id": "BAMLH0A0HYM2", "title": "ICE BofA US High Yield Index Option-Adjusted Spread", "units": "Percent", "units_short": "%", "frequency": "Daily", "frequency_short": "D", "seasonal_adjustment": "Not Seasonally Adjusted"},
        {"series_id": "DTWEXBGS", "title": "Nominal Broad U.S. Dollar Index", "units": "Index", "units_short": "Index", "frequency": "Daily", "frequency_short": "D", "seasonal_adjustment": "Not Seasonally Adjusted"},
    ]
