"""Typed write contracts for the shared SQL repositories."""

from datetime import date, datetime
from decimal import Decimal
from typing import NotRequired, TypedDict

from pydantic import BaseModel, Field


class InstrumentValues(TypedDict):
    symbol: str
    name: str
    country: str
    currency: str
    asset_class: str
    security_type: str
    id: NotRequired[str]
    exchange_id: NotRequired[str | None]
    sector: NotRequired[str | None]
    industry: NotRequired[str | None]
    is_active: NotRequired[bool]
    listing_date: NotRequired[date | None]
    delisting_date: NotRequired[date | None]
    figi: NotRequired[str | None]
    isin: NotRequired[str | None]
    ibkr_contract_id: NotRequired[str | None]


class PriceBarValues(TypedDict):
    instrument_id: str
    timestamp: datetime
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    currency: str
    provider: str
    quality: str
    volume: NotRequired[Decimal | None]
    raw_object_id: NotRequired[str | None]


class MacroSeriesValues(TypedDict):
    series_id: str
    title: str
    units: str
    frequency: str
    units_short: NotRequired[str | None]
    frequency_short: NotRequired[str | None]
    seasonal_adjustment: NotRequired[str | None]
    observation_start: NotRequired[date | None]
    observation_end: NotRequired[date | None]
    last_updated: NotRequired[str | None]
    popularity: NotRequired[int | None]
    notes: NotRequired[str | None]
    provider: NotRequired[str]
    quality: NotRequired[str]
    raw_object_id: NotRequired[str | None]


class MacroObservationValues(TypedDict):
    series_id: str
    observation_date: date
    provider: str
    quality: str
    value: NotRequired[Decimal | None]
    units: NotRequired[str | None]
    realtime_start: NotRequired[date | None]
    realtime_end: NotRequired[date | None]
    vintage_date: NotRequired[date | None]
    release_date: NotRequired[date | None]
    ingestion_timestamp: NotRequired[datetime]
    raw_object_id: NotRequired[str | None]


class TransactionValues(TypedDict):
    portfolio_id: str
    transaction_type: str
    trade_date: date
    currency: str
    source: str
    quality: str
    account_id: NotRequired[str | None]
    instrument_id: NotRequired[str | None]
    settle_date: NotRequired[date | None]
    quantity: NotRequired[Decimal]
    price: NotRequired[Decimal]
    fx_rate_to_base: NotRequired[Decimal]
    fee: NotRequired[Decimal]
    notes: NotRequired[str | None]


class PerformanceValues(TypedDict):
    as_of: datetime
    twr: Decimal
    cagr: Decimal
    volatility: Decimal
    sharpe: Decimal
    sortino: Decimal
    max_drawdown: Decimal
    quality: str


class RiskValues(TypedDict):
    as_of: datetime
    beta: Decimal
    volatility: Decimal
    var_95: Decimal
    cvar_95: Decimal
    max_drawdown: Decimal
    gross_exposure: Decimal
    net_exposure: Decimal
    concentration: Decimal
    quality: str


class JobUpdate(TypedDict, total=False):
    status: str
    progress: Decimal | float | int
    records_received: int
    records_accepted: int
    records_rejected: int
    retry_count: int
    error_category: str | None
    error_message: str | None
    worker_id: str | None
    started_at: datetime | None
    finished_at: datetime | None


class UploadValues(TypedDict):
    original_filename: str
    content_type: str
    object_key: str
    content_hash: str
    size_bytes: int
    upload_state: NotRequired[str]


class DatasetColumnSpec(BaseModel):
    name: str = Field(min_length=1)
    type: str = Field(min_length=1)
    role: str | None = None


class DatasetSchema(BaseModel):
    columns: list[DatasetColumnSpec] = Field(default_factory=list)
