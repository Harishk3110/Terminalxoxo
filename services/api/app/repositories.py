from __future__ import annotations

from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Select, and_, delete, func, or_, select
from sqlalchemy.orm import Session

from . import models


class RepositoryError(RuntimeError):
    pass


def first_or_none[T](session: Session, stmt: Select[tuple[T]]) -> T | None:
    return session.execute(stmt).scalars().first()


class AuditRepository:
    def __init__(self, session: Session):
        self.session = session

    def record(self, *, action: str, resource_type: str, correlation_id: str, resource_id: str | None = None, metadata: dict | None = None) -> models.AuditLog:
        item = models.AuditLog(action=action, resource_type=resource_type, resource_id=resource_id, correlation_id=correlation_id, metadata_json=metadata)
        self.session.add(item)
        return item


class ProviderRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_connection(self, *, provider_name: str, provider_type: str, enabled: bool, configured: bool, state: str, capabilities: list[str], masked_identifier: str | None = None, last_error: str | None = None) -> models.ProviderConnection:
        item = first_or_none(self.session, select(models.ProviderConnection).where(models.ProviderConnection.provider_name == provider_name))
        if item is None:
            item = models.ProviderConnection(provider_name=provider_name, provider_type=provider_type)
            self.session.add(item)
        item.enabled = enabled
        item.configured = configured
        item.connection_state = state
        item.capabilities = capabilities
        item.masked_identifier = masked_identifier
        item.last_error = last_error
        if state == "CONNECTED":
            item.last_success = models.utcnow()
        elif state in {"FAILED", "NOT_CONFIGURED"}:
            item.last_failure = models.utcnow() if state == "FAILED" else item.last_failure
        return item

    def list_connections(self) -> list[models.ProviderConnection]:
        return list(self.session.execute(select(models.ProviderConnection).order_by(models.ProviderConnection.provider_name)).scalars())

    def record_health(self, provider_name: str, state: str, latency_ms: int | None = None, error_message: str | None = None) -> models.ProviderHealthSnapshot:
        item = models.ProviderHealthSnapshot(provider_name=provider_name, state=state, latency_ms=latency_ms, error_message=error_message)
        self.session.add(item)
        return item


class RawObjectRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, *, provider: str, dataset: str, object_key: str, content_hash: str, content_type: str, size_bytes: int, source_uri: str | None, correlation_id: str) -> models.RawObject:
        existing = first_or_none(self.session, select(models.RawObject).where(models.RawObject.object_key == object_key))
        if existing:
            return existing
        item = models.RawObject(
            provider=provider,
            dataset=dataset,
            object_key=object_key,
            content_hash=content_hash,
            content_type=content_type,
            size_bytes=size_bytes,
            source_uri=source_uri,
            correlation_id=correlation_id,
        )
        self.session.add(item)
        self.session.flush()
        return item


class InstrumentRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_exchange(self, code: str, name: str, country: str, timezone: str) -> models.Exchange:
        item = first_or_none(self.session, select(models.Exchange).where(models.Exchange.code == code))
        if item is None:
            item = models.Exchange(code=code, name=name, country=country, timezone=timezone)
            self.session.add(item)
            self.session.flush()
        return item

    def upsert_currency(self, code: str, name: str) -> models.Currency:
        item = first_or_none(self.session, select(models.Currency).where(models.Currency.code == code))
        if item is None:
            item = models.Currency(code=code, name=name)
            self.session.add(item)
        return item

    def upsert_instrument(self, **kwargs: Any) -> models.Instrument:
        stmt = select(models.Instrument).where(and_(models.Instrument.symbol == kwargs["symbol"], models.Instrument.exchange_id == kwargs.get("exchange_id")))
        item = first_or_none(self.session, stmt)
        if item is None:
            item = models.Instrument(**kwargs)
            self.session.add(item)
            self.session.flush()
        else:
            for key, value in kwargs.items():
                setattr(item, key, value)
        return item

    def list(self, limit: int = 100, offset: int = 0, query: str | None = None) -> list[models.Instrument]:
        stmt = select(models.Instrument).order_by(models.Instrument.symbol).limit(limit).offset(offset)
        if query:
            pattern = f"%{query.upper()}%"
            stmt = select(models.Instrument).where(or_(models.Instrument.symbol.ilike(pattern), models.Instrument.name.ilike(f"%{query}%"))).order_by(models.Instrument.symbol).limit(limit).offset(offset)
        return list(self.session.execute(stmt).scalars())

    def get(self, instrument_id: str) -> models.Instrument | None:
        return self.session.get(models.Instrument, instrument_id)

    def by_symbol(self, symbol: str) -> models.Instrument | None:
        return first_or_none(self.session, select(models.Instrument).where(models.Instrument.symbol == symbol))


class MarketRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_quote(self, instrument_id: str, price: Decimal, currency: str, as_of: datetime, provider: str, quality: str) -> models.LatestQuote:
        item = first_or_none(self.session, select(models.LatestQuote).where(models.LatestQuote.instrument_id == instrument_id))
        if item is None:
            item = models.LatestQuote(instrument_id=instrument_id, price=price, currency=currency, as_of=as_of, provider=provider, quality=quality)
            self.session.add(item)
        else:
            item.price = price
            item.currency = currency
            item.as_of = as_of
            item.provider = provider
            item.quality = quality
        return item

    def latest_quote(self, instrument_id: str) -> models.LatestQuote | None:
        return first_or_none(self.session, select(models.LatestQuote).where(models.LatestQuote.instrument_id == instrument_id))

    def insert_price_bar(self, **kwargs: Any) -> models.PriceBar | None:
        exists = first_or_none(
            self.session,
            select(models.PriceBar).where(
                and_(
                    models.PriceBar.instrument_id == kwargs["instrument_id"],
                    models.PriceBar.timestamp == kwargs["timestamp"],
                    models.PriceBar.interval == kwargs["interval"],
                    models.PriceBar.provider == kwargs["provider"],
                )
            ),
        )
        if exists:
            return None
        item = models.PriceBar(**kwargs)
        self.session.add(item)
        return item

    def price_history(self, instrument_id: str, interval: str = "1d", limit: int = 3000) -> list[models.PriceBar]:
        stmt = (
            select(models.PriceBar)
            .where(and_(models.PriceBar.instrument_id == instrument_id, models.PriceBar.interval == interval))
            .order_by(models.PriceBar.timestamp.desc())
            .limit(limit)
        )
        return list(reversed(self.session.execute(stmt).scalars().all()))

    def upsert_fx(self, base: str, quote: str, value_date: date, rate: Decimal, provider: str, quality: str) -> None:
        item = first_or_none(
            self.session,
            select(models.FxRate).where(and_(models.FxRate.base_currency == base, models.FxRate.quote_currency == quote, models.FxRate.date == value_date, models.FxRate.provider == provider)),
        )
        if item is None:
            self.session.add(models.FxRate(base_currency=base, quote_currency=quote, date=value_date, rate=rate, provider=provider, quality=quality))
        else:
            item.rate = rate

    def fx_rate(self, base: str, quote: str, on_date: date | None = None) -> Decimal:
        if base == quote:
            return Decimal("1")
        stmt = select(models.FxRate).where(and_(models.FxRate.base_currency == base, models.FxRate.quote_currency == quote)).order_by(models.FxRate.date.desc())
        if on_date:
            stmt = select(models.FxRate).where(and_(models.FxRate.base_currency == base, models.FxRate.quote_currency == quote, models.FxRate.date <= on_date)).order_by(models.FxRate.date.desc())
        row = first_or_none(self.session, stmt)
        if row:
            return Decimal(row.rate)
        inverse = first_or_none(self.session, select(models.FxRate).where(and_(models.FxRate.base_currency == quote, models.FxRate.quote_currency == base)).order_by(models.FxRate.date.desc()))
        if inverse:
            return Decimal("1") / Decimal(inverse.rate)
        raise RepositoryError(f"Missing FX rate {base}/{quote}")


class MacroRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_series(self, **kwargs: Any) -> models.MacroSeries:
        item = first_or_none(self.session, select(models.MacroSeries).where(models.MacroSeries.series_id == kwargs["series_id"]))
        if item is None:
            item = models.MacroSeries(**kwargs)
            self.session.add(item)
            self.session.flush()
        else:
            for key, value in kwargs.items():
                setattr(item, key, value)
        return item

    def insert_observation(self, **kwargs: Any) -> models.MacroObservation | None:
        stmt = select(models.MacroObservation).where(
            and_(
                models.MacroObservation.series_id == kwargs["series_id"],
                models.MacroObservation.observation_date == kwargs["observation_date"],
                models.MacroObservation.realtime_start == kwargs.get("realtime_start"),
                models.MacroObservation.realtime_end == kwargs.get("realtime_end"),
                models.MacroObservation.vintage_date == kwargs.get("vintage_date"),
            )
        )
        if first_or_none(self.session, stmt):
            return None
        item = models.MacroObservation(**kwargs)
        self.session.add(item)
        return item

    def list_series(self, query: str | None = None) -> list[models.MacroSeries]:
        stmt = select(models.MacroSeries).order_by(models.MacroSeries.series_id)
        if query:
            stmt = select(models.MacroSeries).where(or_(models.MacroSeries.series_id.ilike(f"%{query}%"), models.MacroSeries.title.ilike(f"%{query}%"))).order_by(models.MacroSeries.series_id)
        return list(self.session.execute(stmt).scalars())

    def get_series(self, series_id: str) -> models.MacroSeries | None:
        return first_or_none(self.session, select(models.MacroSeries).where(models.MacroSeries.series_id == series_id))

    def observations(self, series_id: str, limit: int = 4000) -> list[models.MacroObservation]:
        stmt = select(models.MacroObservation).where(models.MacroObservation.series_id == series_id).order_by(models.MacroObservation.observation_date.desc()).limit(limit)
        return list(reversed(self.session.execute(stmt).scalars().all()))

    def latest_pair(self, series_id: str) -> tuple[models.MacroObservation | None, models.MacroObservation | None]:
        rows = list(
            self.session.execute(
                select(models.MacroObservation).where(models.MacroObservation.series_id == series_id).order_by(models.MacroObservation.observation_date.desc()).limit(2)
            ).scalars()
        )
        return (rows[0] if rows else None, rows[1] if len(rows) > 1 else None)


class PortfolioRepository:
    def __init__(self, session: Session):
        self.session = session

    def default_portfolio(self) -> models.Portfolio | None:
        return first_or_none(self.session, select(models.Portfolio).where(models.Portfolio.is_default.is_(True)))

    def transactions(self, portfolio_id: str) -> list[models.PortfolioTransaction]:
        return list(self.session.execute(select(models.PortfolioTransaction).where(models.PortfolioTransaction.portfolio_id == portfolio_id).order_by(models.PortfolioTransaction.trade_date, models.PortfolioTransaction.created_at)).scalars())

    def positions(self, portfolio_id: str) -> list[models.PortfolioPosition]:
        return list(self.session.execute(select(models.PortfolioPosition).where(models.PortfolioPosition.portfolio_id == portfolio_id).order_by(models.PortfolioPosition.market_value.desc())).scalars())

    def cash(self, portfolio_id: str) -> list[models.PortfolioCashBalance]:
        return list(self.session.execute(select(models.PortfolioCashBalance).where(models.PortfolioCashBalance.portfolio_id == portfolio_id).order_by(models.PortfolioCashBalance.currency)).scalars())

    def add_transaction(self, **kwargs: Any) -> models.PortfolioTransaction:
        item = models.PortfolioTransaction(**kwargs)
        self.session.add(item)
        self.session.flush()
        return item

    def replace_positions(self, portfolio_id: str, positions: Iterable[models.PortfolioPosition], cash: Iterable[models.PortfolioCashBalance], nav: models.NavSnapshot) -> None:
        self.session.execute(delete(models.PortfolioPosition).where(models.PortfolioPosition.portfolio_id == portfolio_id))
        self.session.execute(delete(models.PortfolioCashBalance).where(models.PortfolioCashBalance.portfolio_id == portfolio_id))
        for item in positions:
            self.session.add(item)
        for item in cash:
            self.session.add(item)
        existing_nav = first_or_none(self.session, select(models.NavSnapshot).where(and_(models.NavSnapshot.portfolio_id == nav.portfolio_id, models.NavSnapshot.as_of == nav.as_of)))
        if existing_nav is None:
            self.session.add(nav)
        else:
            existing_nav.nav = nav.nav
            existing_nav.cash = nav.cash
            existing_nav.market_value = nav.market_value
            existing_nav.quality = nav.quality

    def latest_nav(self, portfolio_id: str) -> models.NavSnapshot | None:
        return first_or_none(self.session, select(models.NavSnapshot).where(models.NavSnapshot.portfolio_id == portfolio_id).order_by(models.NavSnapshot.as_of.desc()))


class AnalyticsRepository:
    def __init__(self, session: Session):
        self.session = session

    def upsert_performance(self, portfolio_id: str, **kwargs: Any) -> models.PerformanceSnapshot:
        item = first_or_none(self.session, select(models.PerformanceSnapshot).where(models.PerformanceSnapshot.portfolio_id == portfolio_id).order_by(models.PerformanceSnapshot.as_of.desc()))
        if item is None:
            item = models.PerformanceSnapshot(portfolio_id=portfolio_id, **kwargs)
            self.session.add(item)
        else:
            for key, value in kwargs.items():
                setattr(item, key, value)
        return item

    def latest_performance(self, portfolio_id: str) -> models.PerformanceSnapshot | None:
        return first_or_none(self.session, select(models.PerformanceSnapshot).where(models.PerformanceSnapshot.portfolio_id == portfolio_id).order_by(models.PerformanceSnapshot.as_of.desc()))

    def upsert_risk(self, portfolio_id: str, **kwargs: Any) -> models.RiskSnapshot:
        item = first_or_none(self.session, select(models.RiskSnapshot).where(models.RiskSnapshot.portfolio_id == portfolio_id).order_by(models.RiskSnapshot.as_of.desc()))
        if item is None:
            item = models.RiskSnapshot(portfolio_id=portfolio_id, **kwargs)
            self.session.add(item)
        else:
            for key, value in kwargs.items():
                setattr(item, key, value)
        return item

    def latest_risk(self, portfolio_id: str) -> models.RiskSnapshot | None:
        return first_or_none(self.session, select(models.RiskSnapshot).where(models.RiskSnapshot.portfolio_id == portfolio_id).order_by(models.RiskSnapshot.as_of.desc()))

    def list_stress_results(self, portfolio_id: str) -> list[models.StressResult]:
        return list(self.session.execute(select(models.StressResult).where(models.StressResult.portfolio_id == portfolio_id).order_by(models.StressResult.created_at.desc())).scalars())

    def latest_hedge(self, portfolio_id: str) -> models.HedgeRecommendation | None:
        return first_or_none(self.session, select(models.HedgeRecommendation).where(models.HedgeRecommendation.portfolio_id == portfolio_id).order_by(models.HedgeRecommendation.created_at.desc()))


class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, *, job_type: str, provider: str | None, parameters: dict | None, correlation_id: str) -> models.IngestionJob:
        item = models.IngestionJob(job_type=job_type, provider=provider, parameters=parameters, correlation_id=correlation_id, status="PENDING")
        self.session.add(item)
        self.session.flush()
        return item

    def get(self, job_id: str) -> models.IngestionJob | None:
        return self.session.get(models.IngestionJob, job_id)

    def list(self, status: str | None = None) -> list[models.IngestionJob]:
        stmt = select(models.IngestionJob).order_by(models.IngestionJob.created_at.desc()).limit(200)
        if status:
            stmt = select(models.IngestionJob).where(models.IngestionJob.status == status).order_by(models.IngestionJob.created_at.desc()).limit(200)
        return list(self.session.execute(stmt).scalars())

    def update(self, job: models.IngestionJob, **kwargs: Any) -> models.IngestionJob:
        for key, value in kwargs.items():
            setattr(job, key, value)
        return job


class DatasetRepository:
    def __init__(self, session: Session):
        self.session = session

    def create_upload(self, **kwargs: Any) -> models.UploadedFile:
        item = models.UploadedFile(**kwargs)
        self.session.add(item)
        self.session.flush()
        return item

    def create_dataset_version(self, *, dataset_name: str, dataset_type: str, source: str, quality: str, raw_object_id: str, row_count: int, content_hash: str, schema_json: dict) -> tuple[models.Dataset, models.DatasetVersion]:
        dataset = models.Dataset(name=dataset_name, dataset_type=dataset_type, source=source, quality=quality)
        self.session.add(dataset)
        self.session.flush()
        version = models.DatasetVersion(dataset_id=dataset.id, version=1, raw_object_id=raw_object_id, row_count=row_count, content_hash=content_hash, schema_json=schema_json)
        self.session.add(version)
        self.session.flush()
        for column in schema_json.get("columns", []):
            self.session.add(models.DatasetColumn(dataset_version_id=version.id, name=column["name"], inferred_type=column["type"], mapped_role=column.get("role")))
        return dataset, version

    def list_datasets(self) -> list[models.Dataset]:
        return list(self.session.execute(select(models.Dataset).order_by(models.Dataset.created_at.desc())).scalars())


class StrategyRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_strategies(self) -> list[models.StrategyDefinition]:
        return list(self.session.execute(select(models.StrategyDefinition).order_by(models.StrategyDefinition.name)).scalars())

    def latest_version(self, strategy_id: str) -> models.StrategyVersion | None:
        return first_or_none(self.session, select(models.StrategyVersion).where(models.StrategyVersion.strategy_id == strategy_id).order_by(models.StrategyVersion.version.desc()))

    def backtest_runs(self) -> list[models.BacktestRun]:
        return list(self.session.execute(select(models.BacktestRun).order_by(models.BacktestRun.created_at.desc())).scalars())

    def backtest_metrics(self, run_id: str) -> list[models.BacktestMetric]:
        return list(self.session.execute(select(models.BacktestMetric).where(models.BacktestMetric.backtest_run_id == run_id).order_by(models.BacktestMetric.metric)).scalars())

    def backtest_curve(self, run_id: str) -> list[models.BacktestEquityCurve]:
        return list(self.session.execute(select(models.BacktestEquityCurve).where(models.BacktestEquityCurve.backtest_run_id == run_id).order_by(models.BacktestEquityCurve.date)).scalars())


class SystemRepository:
    def __init__(self, session: Session):
        self.session = session

    def counts(self) -> dict[str, int]:
        tables = {
            "instruments": models.Instrument,
            "macro_series": models.MacroSeries,
            "macro_observations": models.MacroObservation,
            "transactions": models.PortfolioTransaction,
            "jobs": models.IngestionJob,
            "datasets": models.Dataset,
            "backtests": models.BacktestRun,
            "alerts": models.Alert,
            "data_quality_issues": models.DataQualityIssue,
            "system_health_snapshots": models.SystemHealthSnapshot,
            "research_notes": models.ResearchNote,
            "factor_runs": models.FactorRun,
        }
        return {name: int(self.session.execute(select(func.count()).select_from(model)).scalar_one()) for name, model in tables.items()}
