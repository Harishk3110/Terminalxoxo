from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column


from .schema import Base as Base, IdMixin, TimestampMixin as TimestampMixin, utcnow as utcnow, uuid_pk as uuid_pk
from .ledger_models import PositionLot as PositionLot, PositionLotMatch as PositionLotMatch, TransactionRevision as TransactionRevision
from .accounting_models import CapitalFlow as CapitalFlow, PortfolioIncome as PortfolioIncome, PortfolioFee as PortfolioFee, PortfolioAccrual as PortfolioAccrual, PortfolioLiability as PortfolioLiability
from .auth_models import TotpState as TotpState


class User(IdMixin, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="ADMIN", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class UserSession(IdMixin, Base):
    __tablename__ = "user_sessions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    session_hash: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TotpSetting(IdMixin, Base):
    __tablename__ = "totp_settings"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True)
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RecoveryCode(IdMixin, Base):
    __tablename__ = "recovery_codes"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LoginAttempt(IdMixin, Base):
    __tablename__ = "login_attempts"
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    success: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(80))
    user_agent: Mapped[str | None] = mapped_column(Text)
    failure_reason: Mapped[str | None] = mapped_column(Text)


class Currency(IdMixin, Base):
    __tablename__ = "currencies"
    code: Mapped[str] = mapped_column(String(3), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)


class Exchange(IdMixin, Base):
    __tablename__ = "exchanges"
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    timezone: Mapped[str] = mapped_column(String(80), nullable=False)


class Benchmark(IdMixin, Base):
    __tablename__ = "benchmarks"
    symbol: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)


class Instrument(IdMixin, Base):
    __tablename__ = "instruments"
    symbol: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    exchange_id: Mapped[str | None] = mapped_column(ForeignKey("exchanges.id"), index=True)
    country: Mapped[str] = mapped_column(String(80), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    asset_class: Mapped[str] = mapped_column(String(60), nullable=False)
    security_type: Mapped[str] = mapped_column(String(60), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(120))
    industry: Mapped[str | None] = mapped_column(String(160))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    listing_date: Mapped[datetime | None] = mapped_column(Date)
    delisting_date: Mapped[datetime | None] = mapped_column(Date)
    figi: Mapped[str | None] = mapped_column(String(32))
    isin: Mapped[str | None] = mapped_column(String(32))
    ibkr_contract_id: Mapped[str | None] = mapped_column(String(80))
    __table_args__ = (UniqueConstraint("symbol", "exchange_id", name="uq_instrument_symbol_exchange"),)


class InstrumentIdentifier(IdMixin, Base):
    __tablename__ = "instrument_identifiers"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    identifier_type: Mapped[str] = mapped_column(String(60), nullable=False)
    identifier_value: Mapped[str] = mapped_column(String(160), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(120))
    __table_args__ = (UniqueConstraint("identifier_type", "identifier_value", "provider", name="uq_identifier_provider"),)


class ProviderInstrumentMapping(IdMixin, Base):
    __tablename__ = "provider_instrument_mappings"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_symbol: Mapped[str] = mapped_column(String(160), nullable=False)
    provider_metadata: Mapped[dict | None] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("provider", "provider_symbol", name="uq_provider_symbol"),)


class ProviderConnection(IdMixin, Base):
    __tablename__ = "provider_connections"
    provider_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(80), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    configured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    connection_state: Mapped[str] = mapped_column(String(40), default="NOT_CONFIGURED", nullable=False)
    capabilities: Mapped[list | None] = mapped_column(JSON)
    masked_identifier: Mapped[str | None] = mapped_column(String(120))
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    last_data_sync: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_freshness: Mapped[str | None] = mapped_column(String(40))


class ProviderHealthSnapshot(IdMixin, Base):
    __tablename__ = "provider_health_snapshots"
    provider_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)


class ProviderRequestLog(IdMixin, Base):
    __tablename__ = "provider_request_logs"
    provider_name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(240), nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    correlation_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text)


class ProviderRateLimitState(IdMixin, Base):
    __tablename__ = "provider_rate_limit_states"
    provider_name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    remaining: Mapped[int | None] = mapped_column(Integer)
    reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(40), default="UNKNOWN", nullable=False)


class RawObject(IdMixin, Base):
    __tablename__ = "raw_objects"
    provider: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    dataset: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    object_key: Mapped[str] = mapped_column(String(400), unique=True, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)


class MacroSeries(IdMixin, Base):
    __tablename__ = "macro_series"
    series_id: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    units: Mapped[str] = mapped_column(String(160), nullable=False)
    units_short: Mapped[str | None] = mapped_column(String(60))
    frequency: Mapped[str] = mapped_column(String(80), nullable=False)
    frequency_short: Mapped[str | None] = mapped_column(String(20))
    seasonal_adjustment: Mapped[str | None] = mapped_column(String(120))
    observation_start: Mapped[datetime | None] = mapped_column(Date)
    observation_end: Mapped[datetime | None] = mapped_column(Date)
    last_updated: Mapped[str | None] = mapped_column(String(80))
    popularity: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(120), default="DEMO", nullable=False)
    quality: Mapped[str] = mapped_column(String(40), default="DEMO DATA", nullable=False)
    raw_object_id: Mapped[str | None] = mapped_column(ForeignKey("raw_objects.id"))


class MacroObservation(IdMixin, Base):
    __tablename__ = "macro_observations"
    series_id: Mapped[str] = mapped_column(ForeignKey("macro_series.series_id"), nullable=False, index=True)
    observation_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    units: Mapped[str | None] = mapped_column(String(160))
    realtime_start: Mapped[datetime | None] = mapped_column(Date)
    realtime_end: Mapped[datetime | None] = mapped_column(Date)
    vintage_date: Mapped[datetime | None] = mapped_column(Date)
    release_date: Mapped[datetime | None] = mapped_column(Date)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)
    ingestion_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    raw_object_id: Mapped[str | None] = mapped_column(ForeignKey("raw_objects.id"))
    __table_args__ = (
        UniqueConstraint("series_id", "observation_date", "realtime_start", "realtime_end", "vintage_date", name="uq_macro_observation_version"),
        Index("ix_macro_series_date", "series_id", "observation_date"),
    )


class MacroRelease(IdMixin, Base):
    __tablename__ = "macro_releases"
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    release_id: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    release_date: Mapped[datetime | None] = mapped_column(Date)
    raw_object_id: Mapped[str | None] = mapped_column(ForeignKey("raw_objects.id"))
    __table_args__ = (UniqueConstraint("provider", "release_id", "release_date", name="uq_macro_release"),)


class MacroVintage(IdMixin, Base):
    __tablename__ = "macro_vintages"
    series_id: Mapped[str] = mapped_column(ForeignKey("macro_series.series_id"), nullable=False, index=True)
    vintage_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    raw_object_id: Mapped[str | None] = mapped_column(ForeignKey("raw_objects.id"))
    __table_args__ = (UniqueConstraint("series_id", "vintage_date", "provider", name="uq_macro_vintage"),)


class PriceBar(IdMixin, Base):
    __tablename__ = "price_bars"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    interval: Mapped[str] = mapped_column(String(20), nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    volume: Mapped[Decimal | None] = mapped_column(Numeric(24, 4))
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)
    raw_object_id: Mapped[str | None] = mapped_column(ForeignKey("raw_objects.id"))
    __table_args__ = (UniqueConstraint("instrument_id", "timestamp", "interval", "provider", name="uq_price_bar"),)


class LatestQuote(IdMixin, Base):
    __tablename__ = "latest_quotes"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, unique=True)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)


class FxRate(IdMixin, Base):
    __tablename__ = "fx_rates"
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)
    __table_args__ = (UniqueConstraint("base_currency", "quote_currency", "date", "provider", name="uq_fx_rate"),)


class CorporateAction(IdMixin, Base):
    __tablename__ = "corporate_actions"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String(60), nullable=False)
    effective_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)


class Dataset(IdMixin, Base):
    __tablename__ = "datasets"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dataset_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source: Mapped[str] = mapped_column(String(160), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)


class DatasetVersion(IdMixin, Base):
    __tablename__ = "dataset_versions"
    dataset_id: Mapped[str | None] = mapped_column(ForeignKey("datasets.id"), index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_object_id: Mapped[str] = mapped_column(ForeignKey("raw_objects.id"), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_json: Mapped[dict | None] = mapped_column(JSON)
    __table_args__ = (UniqueConstraint("dataset_id", "version", name="uq_dataset_version"),)


class DatasetColumn(IdMixin, Base):
    __tablename__ = "dataset_columns"
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    inferred_type: Mapped[str] = mapped_column(String(80), nullable=False)
    mapped_role: Mapped[str | None] = mapped_column(String(80))


class DatasetLineage(IdMixin, Base):
    __tablename__ = "dataset_lineage"
    dataset_version_id: Mapped[str] = mapped_column(ForeignKey("dataset_versions.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    transform: Mapped[str] = mapped_column(Text, nullable=False)


class UploadedFile(IdMixin, Base):
    __tablename__ = "uploaded_files"
    original_filename: Mapped[str] = mapped_column(String(260), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    object_key: Mapped[str] = mapped_column(String(400), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    upload_state: Mapped[str] = mapped_column(String(40), default="STORED", nullable=False)


class IngestionJob(IdMixin, Base):
    __tablename__ = "ingestion_jobs"
    job_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(String(120), index=True)
    parameters: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False, index=True)
    progress: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=0, nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_accepted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_category: Mapped[str | None] = mapped_column(String(120))
    error_message: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    worker_id: Mapped[str | None] = mapped_column(String(120))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("progress >= 0 AND progress <= 1", name="ck_job_progress"),)


class IngestionJobRun(IdMixin, Base):
    __tablename__ = "ingestion_job_runs"
    job_id: Mapped[str] = mapped_column(ForeignKey("ingestion_jobs.id"), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    log_payload: Mapped[dict | None] = mapped_column(JSON)


class DataQualityIssue(IdMixin, Base):
    __tablename__ = "data_quality_issues"
    dataset: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(120), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuarantineRecord(IdMixin, Base):
    __tablename__ = "quarantine_records"
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    row_number: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict | None] = mapped_column(JSON)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)


class Portfolio(IdMixin, Base):
    __tablename__ = "portfolios"
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    reference_capital: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)


class PortfolioAccount(IdMixin, Base):
    __tablename__ = "portfolio_accounts"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    account_type: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    provider: Mapped[str | None] = mapped_column(String(120))


class PortfolioTransaction(IdMixin, Base):
    __tablename__ = "portfolio_transactions"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    account_id: Mapped[str | None] = mapped_column(ForeignKey("portfolio_accounts.id"), index=True)
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("instruments.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(40), nullable=False)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    settle_date: Mapped[datetime | None] = mapped_column(Date)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    fx_rate_to_base: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=1, nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (Index("ix_portfolio_txn_portfolio_date", "portfolio_id", "trade_date"),)


class PortfolioPosition(IdMixin, Base):
    __tablename__ = "portfolio_positions"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    average_cost: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    market_price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    unrealised_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    realised_pnl: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0, nullable=False)
    weight: Mapped[Decimal] = mapped_column(Numeric(18, 8), default=0, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)
    __table_args__ = (UniqueConstraint("portfolio_id", "instrument_id", name="uq_portfolio_position"),)


class PortfolioCashBalance(IdMixin, Base):
    __tablename__ = "portfolio_cash_balances"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)
    __table_args__ = (UniqueConstraint("portfolio_id", "currency", name="uq_portfolio_cash_currency"),)


class CashFlow(IdMixin, Base):
    __tablename__ = "cash_flows"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    flow_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    flow_type: Mapped[str] = mapped_column(String(60), nullable=False)


class NavSnapshot(IdMixin, Base):
    __tablename__ = "nav_snapshots"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    nav: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)
    __table_args__ = (UniqueConstraint("portfolio_id", "as_of", name="uq_nav_snapshot"),)


class DailyReturn(IdMixin, Base):
    __tablename__ = "daily_returns"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False, index=True)
    return_value: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    __table_args__ = (UniqueConstraint("portfolio_id", "date", name="uq_daily_return"),)


class BenchmarkReturn(IdMixin, Base):
    __tablename__ = "benchmark_returns"
    benchmark_id: Mapped[str] = mapped_column(ForeignKey("benchmarks.id"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    return_value: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    __table_args__ = (UniqueConstraint("benchmark_id", "date", name="uq_benchmark_return"),)


class TargetAllocation(IdMixin, Base):
    __tablename__ = "target_allocations"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    target_weight: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)


class PerformanceSnapshot(IdMixin, Base):
    __tablename__ = "performance_snapshots"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    twr: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    cagr: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    volatility: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    sharpe: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    sortino: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)


class RiskPolicy(IdMixin, Base):
    __tablename__ = "risk_policies"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class RiskLimit(IdMixin, Base):
    __tablename__ = "risk_limits"
    policy_id: Mapped[str] = mapped_column(ForeignKey("risk_policies.id"), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)


class RiskSnapshot(IdMixin, Base):
    __tablename__ = "risk_snapshots"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    beta: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    volatility: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    var_95: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    cvar_95: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    max_drawdown: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    gross_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    net_exposure: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    concentration: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)


class RiskBreach(IdMixin, Base):
    __tablename__ = "risk_breaches"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    limit_id: Mapped[str | None] = mapped_column(ForeignKey("risk_limits.id"))
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    observed_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    threshold: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False)


class StressScenario(IdMixin, Base):
    __tablename__ = "stress_scenarios"
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    shocks: Mapped[dict] = mapped_column(JSON, nullable=False)


class StressResult(IdMixin, Base):
    __tablename__ = "stress_results"
    scenario_id: Mapped[str] = mapped_column(ForeignKey("stress_scenarios.id"), nullable=False, index=True)
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    pnl_impact: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    nav_after: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    contributions: Mapped[list | None] = mapped_column(JSON)


class HedgeInstrument(IdMixin, Base):
    __tablename__ = "hedge_instruments"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, unique=True)
    hedge_type: Mapped[str] = mapped_column(String(60), nullable=False)
    beta: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    contract_multiplier: Mapped[Decimal] = mapped_column(Numeric(18, 4), default=1, nullable=False)


class HedgeRecommendation(IdMixin, Base):
    __tablename__ = "hedge_recommendations"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    target_beta: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    current_beta: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    target_notional: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    residual_notional: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)


class HedgeRecommendationItem(IdMixin, Base):
    __tablename__ = "hedge_recommendation_items"
    recommendation_id: Mapped[str] = mapped_column(ForeignKey("hedge_recommendations.id"), nullable=False, index=True)
    hedge_instrument_id: Mapped[str] = mapped_column(ForeignKey("hedge_instruments.id"), nullable=False)
    units: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    notional: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)


class StrategyDefinition(IdMixin, Base):
    __tablename__ = "strategy_definitions"
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    strategy_type: Mapped[str] = mapped_column(String(80), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class StrategyVersion(IdMixin, Base):
    __tablename__ = "strategy_versions"
    strategy_id: Mapped[str] = mapped_column(ForeignKey("strategy_definitions.id"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("strategy_id", "version", name="uq_strategy_version"),)


class StrategyParameter(IdMixin, Base):
    __tablename__ = "strategy_parameters"
    strategy_version_id: Mapped[str] = mapped_column(ForeignKey("strategy_versions.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    value_json: Mapped[dict | str | int | float | None] = mapped_column(JSON)


class BacktestRun(IdMixin, Base):
    __tablename__ = "backtest_runs"
    strategy_version_id: Mapped[str] = mapped_column(ForeignKey("strategy_versions.id"), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    final_equity: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    parameters: Mapped[dict | None] = mapped_column(JSON)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)


class BacktestMetric(IdMixin, Base):
    __tablename__ = "backtest_metrics"
    backtest_run_id: Mapped[str] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False, index=True)
    metric: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)


class BacktestEquityCurve(IdMixin, Base):
    __tablename__ = "backtest_equity_curve"
    backtest_run_id: Mapped[str] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    equity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    drawdown: Mapped[Decimal] = mapped_column(Numeric(18, 10), nullable=False)
    __table_args__ = (UniqueConstraint("backtest_run_id", "date", name="uq_backtest_equity_date"),)


class BacktestPosition(IdMixin, Base):
    __tablename__ = "backtest_positions"
    backtest_run_id: Mapped[str] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    market_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)


class BacktestTrade(IdMixin, Base):
    __tablename__ = "backtest_trades"
    backtest_run_id: Mapped[str] = mapped_column(ForeignKey("backtest_runs.id"), nullable=False, index=True)
    trade_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    side: Mapped[str] = mapped_column(String(20), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    slippage: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)


class Signal(IdMixin, Base):
    __tablename__ = "signals"
    strategy_version_id: Mapped[str] = mapped_column(ForeignKey("strategy_versions.id"), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    signal_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    signal_value: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)


class FactorDefinition(IdMixin, Base):
    __tablename__ = "factor_definitions"
    name: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    formula: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class FactorRun(IdMixin, Base):
    __tablename__ = "factor_runs"
    factor_id: Mapped[str] = mapped_column(ForeignKey("factor_definitions.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FactorValue(IdMixin, Base):
    __tablename__ = "factor_values"
    factor_run_id: Mapped[str] = mapped_column(ForeignKey("factor_runs.id"), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    value: Mapped[Decimal] = mapped_column(Numeric(24, 10), nullable=False)


class Watchlist(IdMixin, Base):
    __tablename__ = "watchlists"
    name: Mapped[str] = mapped_column(String(160), nullable=False)


class WatchlistItem(IdMixin, Base):
    __tablename__ = "watchlist_items"
    watchlist_id: Mapped[str] = mapped_column(ForeignKey("watchlists.id"), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    __table_args__ = (UniqueConstraint("watchlist_id", "instrument_id", name="uq_watchlist_item"),)


class ResearchNote(IdMixin, Base):
    __tablename__ = "research_notes"
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("instruments.id"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    visibility: Mapped[str] = mapped_column(String(40), nullable=False)


class InvestmentThesis(IdMixin, Base):
    __tablename__ = "investment_theses"
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("instruments.id"), index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    thesis_state: Mapped[str] = mapped_column(String(60), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)


class ThesisSource(IdMixin, Base):
    __tablename__ = "thesis_sources"
    thesis_id: Mapped[str] = mapped_column(ForeignKey("investment_theses.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    citation: Mapped[str] = mapped_column(Text, nullable=False)


class ThesisAttachment(IdMixin, Base):
    __tablename__ = "thesis_attachments"
    thesis_id: Mapped[str] = mapped_column(ForeignKey("investment_theses.id"), nullable=False, index=True)
    uploaded_file_id: Mapped[str | None] = mapped_column(ForeignKey("uploaded_files.id"))
    attachment_type: Mapped[str] = mapped_column(String(80), nullable=False)
    license_notes: Mapped[str | None] = mapped_column(Text)


class DecisionJournal(IdMixin, Base):
    __tablename__ = "decision_journal"
    portfolio_id: Mapped[str | None] = mapped_column(ForeignKey("portfolios.id"), index=True)
    thesis_id: Mapped[str | None] = mapped_column(ForeignKey("investment_theses.id"), index=True)
    decision_type: Mapped[str] = mapped_column(String(80), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


class Alert(IdMixin, Base):
    __tablename__ = "alerts"
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AlertDelivery(IdMixin, Base):
    __tablename__ = "alert_deliveries"
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(80), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivery_state: Mapped[str] = mapped_column(String(40), nullable=False)


class AuditLog(IdMixin, Base):
    __tablename__ = "audit_logs"
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(160), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(120), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(120))
    correlation_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON)


class SystemHealthSnapshot(IdMixin, Base):
    __tablename__ = "system_health_snapshots"
    component: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Workspace(IdMixin, Base):
    __tablename__ = "workspaces"
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)


class WorkspaceTab(IdMixin, Base):
    __tablename__ = "workspace_tabs"
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False, index=True)
    route: Mapped[str] = mapped_column(String(240), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class FavouriteFunction(IdMixin, Base):
    __tablename__ = "favourite_functions"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    function_code: Mapped[str] = mapped_column(String(40), nullable=False)


class RecentCommand(IdMixin, Base):
    __tablename__ = "recent_commands"
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    command: Mapped[str] = mapped_column(String(160), nullable=False)
    route: Mapped[str] = mapped_column(String(240), nullable=False)


class WorkspaceState(IdMixin, Base):
    __tablename__ = "workspace_states"
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), unique=True, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, nullable=False)


class AnalysisRun(IdMixin, Base):
    __tablename__ = "analysis_runs"
    kind: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="QUEUED", nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False)
    result: Mapped[dict | None] = mapped_column(JSON)
    history: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FundamentalSnapshot(IdMixin, Base):
    __tablename__ = "fundamental_snapshots"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, unique=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    quality: Mapped[str] = mapped_column(String(40), nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    statements: Mapped[dict] = mapped_column(JSON, nullable=False)


class PortfolioProfile(IdMixin, Base):
    __tablename__ = "portfolio_profiles"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class TransactionDetail(IdMixin, Base):
    __tablename__ = "transaction_details"
    transaction_id: Mapped[str] = mapped_column(ForeignKey("portfolio_transactions.id"), unique=True, nullable=False)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    commission: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0, nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=0, nullable=False)
    contract_multiplier: Mapped[Decimal] = mapped_column(Numeric(24, 8), default=1, nullable=False)
    base_value: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    external_key: Mapped[str | None] = mapped_column(String(200), unique=True)
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey("external_files.id"), index=True)
    reconciliation_state: Mapped[str] = mapped_column(String(40), default="INTERNAL_ONLY", nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class PortfolioBalanceAdjustment(IdMixin, Base):
    __tablename__ = "portfolio_balance_adjustments"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    effective_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    bucket: Mapped[str] = mapped_column(String(40), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class MarketObservation(IdMixin, Base):
    __tablename__ = "market_observations"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False, index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_category: Mapped[str] = mapped_column(String(30), nullable=False)
    data_state: Mapped[str] = mapped_column(String(40), nullable=False)
    adjustment_state: Mapped[str] = mapped_column(String(40), default="UNADJUSTED", nullable=False)
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey("external_files.id"), index=True)
    fields: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    __table_args__ = (UniqueConstraint("instrument_id", "timestamp", "source", "dataset_version_id", name="uq_observation_source_version"),)


class FxObservation(IdMixin, Base):
    __tablename__ = "fx_observations"
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    rate: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_category: Mapped[str] = mapped_column(String(30), nullable=False)
    data_state: Mapped[str] = mapped_column(String(40), nullable=False)
    source_file_id: Mapped[str | None] = mapped_column(ForeignKey("external_files.id"))


class SourcePrecedenceRule(IdMixin, Base):
    __tablename__ = "source_precedence_rules"
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), unique=True, nullable=False)
    priority: Mapped[list] = mapped_column(JSON, nullable=False)
    preferred_source: Mapped[str | None] = mapped_column(String(120))
    stale_after_hours: Mapped[int] = mapped_column(Integer, default=72, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class PortfolioValuationRun(IdMixin, Base):
    __tablename__ = "portfolio_valuation_runs"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    valuation_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    nav: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class PositionValuation(IdMixin, Base):
    __tablename__ = "position_valuations"
    valuation_run_id: Mapped[str] = mapped_column(ForeignKey("portfolio_valuation_runs.id"), nullable=False, index=True)
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    market_value: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    provenance: Mapped[dict] = mapped_column(JSON, nullable=False)


class TradeEvent(IdMixin, Base):
    __tablename__ = "trade_events"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("portfolio_transactions.id"), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    review_state: Mapped[str] = mapped_column(String(40), default="REQUIRES_REVIEW", nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class TradeReview(IdMixin, Base):
    __tablename__ = "trade_reviews"
    trade_id: Mapped[str] = mapped_column(ForeignKey("trade_events.id"), nullable=False, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str] = mapped_column(Text, nullable=False)


class TradeRiskSnapshot(IdMixin, Base):
    __tablename__ = "trade_risk_snapshots"
    trade_id: Mapped[str] = mapped_column(ForeignKey("trade_events.id"), unique=True, nullable=False)
    before: Mapped[dict] = mapped_column(JSON, nullable=False)
    after: Mapped[dict] = mapped_column(JSON, nullable=False)
    breaches: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class BrokerAccountSnapshot(IdMixin, Base):
    __tablename__ = "broker_account_snapshots"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    external_reference: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    nav: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)


class PortfolioReconciliationBreak(IdMixin, Base):
    __tablename__ = "portfolio_reconciliation_breaks"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False, index=True)
    external_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("broker_account_snapshots.id"))
    break_type: Mapped[str] = mapped_column(String(60), nullable=False)
    state: Mapped[str] = mapped_column(String(40), default="OPEN", nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text)


class MappingProfile(IdMixin, Base):
    __tablename__ = "mapping_profiles"
    code: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    dataset_type: Mapped[str] = mapped_column(String(80), nullable=False)
    approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False)
    __table_args__ = (UniqueConstraint("code", "version", name="uq_mapping_profile_version"),)


class LocalAgent(IdMixin, Base):
    __tablename__ = "local_agents"
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    scopes: Mapped[list] = mapped_column(JSON, nullable=False)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class AgentPairing(IdMixin, Base):
    __tablename__ = "local_agent_pairings"
    code_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scopes: Mapped[list] = mapped_column(JSON, nullable=False)


class ExternalFile(IdMixin, Base):
    __tablename__ = "external_files"
    filename: Mapped[str] = mapped_column(String(260), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(120), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("local_agents.id"), index=True)
    uploaded_file_id: Mapped[str | None] = mapped_column(ForeignKey("uploaded_files.id"))
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("mapping_profiles.id"))
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"), index=True)
    duplicate_of: Mapped[str | None] = mapped_column(ForeignKey("external_files.id"))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    mapping: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    validation: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    history: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class FileHash(IdMixin, Base):
    __tablename__ = "file_hashes"
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    file_id: Mapped[str] = mapped_column(ForeignKey("external_files.id"), unique=True, nullable=False)


class ResearchCandidate(IdMixin, Base):
    __tablename__ = "research_candidates"
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    strategy_id: Mapped[str | None] = mapped_column(ForeignKey("strategy_definitions.id"))
    dataset_version_id: Mapped[str | None] = mapped_column(ForeignKey("dataset_versions.id"))
    state: Mapped[str] = mapped_column(String(40), default="RESEARCH", nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    review: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
