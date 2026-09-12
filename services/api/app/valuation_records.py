"""In-memory valuation records before exact amounts cross the JSON boundary."""

from decimal import Decimal
from typing import NotRequired, TypedDict

from .portfolio_domain.position_metrics import PositionPayload
from .portfolio_domain.position_pnl import PositionPnlPayload
from .price_sources import PriceProvenance


class ValuationPosition(PositionPayload):
    id: str
    instrument_id: str
    symbol: str
    name: str
    currency: str
    sector: str
    country: str
    industry: str
    asset_class: str
    source: str
    quality: str
    as_of: str | None
    price_provenance: PriceProvenance
    fx_provenance: PriceProvenance
    fx_rate: Decimal | None
    weight: Decimal | None
    beta: float | None
    risk_contribution: float | None
    daily_pnl: NotRequired[float | None]
    daily_pnl_details: NotRequired[PositionPnlPayload]
    nav_weight: NotRequired[Decimal | None]
    sector_weight: NotRequired[Decimal | None]
    beta_contribution: NotRequired[Decimal | float | None]
    marginal_volatility: NotRequired[float | None]
    component_volatility: NotRequired[float | None]


class ValuationCash(TypedDict):
    currency: str
    amount: Decimal
    settled: Decimal
    receivable: Decimal
    payable: Decimal
    available: Decimal
    base_value: Decimal | None
    base_value_exact: Decimal | None
    as_of: str | None
    quality: str
    fx_rate: Decimal | None
    fx_provenance: PriceProvenance
    source: str


ValuationDay = TypedDict(
    "ValuationDay",
    {
        "date": str,
        "equity": float | None,
        "opening_nav": float | None,
        "daily_pnl": float | None,
        "external_flow": float | None,
        "return": float | None,
        "nav_exact": Decimal | None,
        "opening_nav_exact": Decimal | None,
        "pnl_exact": Decimal | None,
        "external_flow_exact": Decimal,
        "net_return_exact": Decimal | None,
        "fee_expense_exact": Decimal | None,
        "benchmark": float | None,
        "benchmark_return": float | None,
        "benchmark_return_exact": Decimal | None,
        "drawdown": float | None,
        "return_index": float | None,
        "quality": str,
    },
)
