"""Typed option-analysis payloads shared by calculation and API consumers."""

from typing import Literal, NotRequired, TypedDict

from pydantic import JsonValue

from .price_sources import PriceProvenance
from .quant_data import DatasetProvenance

type DealerConvention = Literal["DEALER_SHORT", "NEUTRAL", "CALL_POSITIVE_PUT_NEGATIVE"]
type CoreGreek = Literal["delta", "gamma", "theta", "vega", "rho"]
type PositionMetric = Literal[
    "delta", "gamma", "theta", "vega", "rho", "dollar_delta", "gamma_1pct"
]


class ProviderGreeks(TypedDict):
    delta: float | None
    gamma: float | None
    theta: float | None
    vega: float | None
    rho: float | None


class AnalysedOption(ProviderGreeks):
    symbol: str
    option_symbol: str
    expiry: str
    expiry_time_utc: str
    strike: float
    right: Literal["CALL", "PUT"]
    multiplier: float
    exercise_style: Literal["EUROPEAN", "AMERICAN"]
    currency: str
    timestamp: str
    iv_unit: Literal["DECIMAL"]
    iv: float | None
    bid: float | None
    ask: float | None
    last: float | None
    volume: int | None
    open_interest: int | None
    oi_change: int | None
    greek_units: Literal["STANDARD", "UNSPECIFIED"]
    age_hours: float
    years: float
    mid: float | None
    state: str
    greek_source: Literal["CALCULATED", "PROVIDER"]
    intrinsic: float
    extrinsic: float | None
    moneyness: float
    provider_greeks: ProviderGreeks
    vanna: float | None
    charm: float | None
    vomma: float | None
    speed: float | None
    color: float | None
    veta: float | None
    zomma: float | None
    ultima: float | None
    gex: float | None
    dex: float | None
    contract_gamma: float | None
    dollar_gamma: float | None
    theoretical_price: float | None
    reason: str | None
    iv_source: NotRequired[str]
    pricing_assumptions: NotRequired[dict[str, JsonValue] | None]


class ExposureTotals(TypedDict):
    call_gex: float | None
    put_gex: float | None
    net_gex: float | None
    dex: float | None
    contracts: int
    included: int


class StrikeExposure(ExposureTotals):
    strike: float


class ExpiryExposure(ExposureTotals):
    expiry: str


class SpotExposure(TypedDict):
    spot: float
    call_gex: float | None
    put_gex: float | None
    net_gex: float | None


class MaxPain(TypedDict):
    expiry: str
    strike: float | None
    payout: float | None
    state: str


class ExpectedMove(TypedDict):
    expiry: str
    atm_strike: float | None
    iv: float | None
    move: float | None


class OptionSkew(TypedDict):
    expiry: str
    call_delta: float | None
    put_delta: float | None
    risk_reversal: float | None
    butterfly: float | None
    state: str


class IvPoint(TypedDict):
    strike: float
    expiry: str
    days: float
    iv: float
    right: Literal["CALL", "PUT"]


class ChainSummary(TypedDict):
    net_gex: float | None
    call_gex: float | None
    put_gex: float | None
    dex: float | None
    call_wall: float | None
    put_wall: float | None
    largest_positive_gamma: float | None
    largest_negative_gamma: float | None
    gamma_concentration: float | None
    put_call_oi: float | None
    put_call_volume: float | None


class ChainCoverage(TypedDict):
    contracts: int
    gex_included: int
    missing_gex: int
    gex_fraction: float
    spot_profile_contracts: int
    confidence: str


class OptionPosition(TypedDict):
    option_symbol: str
    quantity: float
    state: str
    multiplier: NotRequired[float]
    expiry: NotRequired[str]
    delta: NotRequired[float | None]
    gamma: NotRequired[float | None]
    theta: NotRequired[float | None]
    vega: NotRequired[float | None]
    rho: NotRequired[float | None]
    dollar_delta: NotRequired[float | None]
    gamma_1pct: NotRequired[float | None]
    premium: NotRequired[float | None]


class PayoffPoint(TypedDict):
    spot: float
    pnl: float


class PositionAnalysis(TypedDict):
    items: list[OptionPosition]
    totals: dict[PositionMetric, float | None]
    state: str
    equity_quantity: float
    payoff: list[PayoffPoint]
    payoff_state: str
    warnings: list[str]


class ChainAnalysis(TypedDict):
    symbol: str
    currency: str
    spot: float
    items: list[AnalysedOption]
    by_strike: list[StrikeExposure]
    by_expiry: list[ExpiryExposure]
    spot_profile: list[SpotExposure]
    gamma_flips: list[float]
    gamma_flip: float | None
    max_pain: list[MaxPain]
    expected_moves: list[ExpectedMove]
    skew: list[OptionSkew]
    iv_surface: list[IvPoint]
    summary: ChainSummary
    coverage: ChainCoverage
    state: str
    greek_units: dict[str, str]
    dealer_sign: DealerConvention
    calculation_version: str
    as_of: str
    warnings: list[str]
    source: NotRequired[str]
    quality: NotRequired[str]
    inputs: NotRequired[DatasetProvenance]
    spot_provenance: NotRequired[PriceProvenance]
    instrument_id: NotRequired[str]
    valuation_run_id: NotRequired[str]
    unmatched_portfolio_options: NotRequired[list[str]]
    position_source: NotRequired[str]
    positions: NotRequired[PositionAnalysis]
