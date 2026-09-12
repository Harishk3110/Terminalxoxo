"""Typed recorded trade evidence without coercing observations or losing extensions."""

from decimal import Decimal, InvalidOperation
from typing import Annotated, Literal, NotRequired, TypedDict

from pydantic import AfterValidator, ConfigDict, TypeAdapter, WrapValidator, with_config

from .equity_contracts import preserve_source_order
from .price_sources import PriceProvenance


def finite_observation(value: str | int | float) -> str | int | float:
    try:
        valid = Decimal(str(value)).is_finite()
    except InvalidOperation as exc:
        raise ValueError("Recorded observation must be numeric") from exc
    if not valid:
        raise ValueError("Recorded observation must be finite")
    return value


Observation = Annotated[str | int | float, AfterValidator(finite_observation)]
ReviewState = Literal["REQUIRES_REVIEW", "REVIEWED", "FLAGGED"]


class SymbolWeight(TypedDict):
    symbol: str
    weight: NotRequired[Observation | None]


class SectorWeight(TypedDict):
    name: str
    weight: NotRequired[Observation | None]


class RecordedExposures(TypedDict, total=False):
    sector: list[SectorWeight]


class RecordedTradeRisk(TypedDict, total=False):
    nav: Observation | None
    cash: Observation | None
    beta: Observation | None
    gross_exposure: Observation | None
    positions: list[SymbolWeight]
    exposures: RecordedExposures
    as_of: str | None


@with_config(ConfigDict(extra="allow", strict=True, allow_inf_nan=False))
class SnapshotExposure(SectorWeight):
    pass


OrderedSnapshotExposure = Annotated[SnapshotExposure, WrapValidator(preserve_source_order)]


class SnapshotPortfolio(TypedDict):
    nav: Observation | None
    cash: Observation | None


class SnapshotRiskMetrics(TypedDict, total=False):
    beta: Observation | None
    gross_exposure: Observation | None


class SnapshotPosition(TypedDict):
    symbol: str
    weight: Observation | None


class LedgerValuationInput(TypedDict):
    portfolio: SnapshotPortfolio
    risk: SnapshotRiskMetrics
    positions: list[SnapshotPosition]
    exposures: dict[str, list[OrderedSnapshotExposure]]
    as_of: str


class SavedTradeSnapshot(TypedDict):
    nav: Observation | None
    beta: Observation | None
    positions: list[SnapshotPosition]
    exposures: dict[str, list[OrderedSnapshotExposure]]
    cash: NotRequired[Observation | None]
    gross_exposure: NotRequired[Observation | None]
    as_of: NotRequired[str]


@with_config(ConfigDict(extra="allow", strict=True, allow_inf_nan=False))
class TradeMetadata(TypedDict, total=False):
    symbol: str | None
    external_reference: str | None
    source_file_id: str | None
    thesis_id: str | None
    strategy_id: str | None
    rationale: str | None
    risk_method: str | None
    demo_seed: bool
    thesis: str | None


@with_config(ConfigDict(extra="allow", strict=True, allow_inf_nan=False))
class TradeTransaction(TypedDict):
    id: str
    symbol: NotRequired[str | None]
    quantity: NotRequired[Observation | None]
    price: NotRequired[Observation | None]
    gross_amount: NotRequired[Observation | None]
    fee: NotRequired[Observation | None]
    commission: NotRequired[Observation | None]
    tax: NotRequired[Observation | None]
    fx_rate_to_base: NotRequired[Observation | None]
    base_value: NotRequired[Observation | None]
    ledger_state: NotRequired[Literal["ACTIVE", "VOID"]]


@with_config(ConfigDict(extra="allow", strict=True, allow_inf_nan=False))
class TradeBreach(TypedDict):
    metric: str
    severity: str
    state: str
    value: NotRequired[Observation | None]
    threshold: NotRequired[Observation | None]
    symbol: NotRequired[str | None]
    limit_id: NotRequired[str]
    as_of: NotRequired[str | None]


OrderedBreach = Annotated[TradeBreach, WrapValidator(preserve_source_order)]
OrderedProvenance = Annotated[PriceProvenance, WrapValidator(preserve_source_order)]


@with_config(ConfigDict(extra="allow", strict=True, allow_inf_nan=False))
class TradeMonitorRow(TradeTransaction):
    transaction_id: str
    detected_at: str
    review_state: ReviewState
    pre_beta: Observation | None
    post_beta: Observation | None
    weight_before: Observation | None
    weight_after: Observation | None
    sector_weight_before: Observation | None
    sector_weight_after: Observation | None
    risk_as_of: str | None
    current_price: Observation | None
    current_price_provenance: OrderedProvenance | None
    breaches: list[OrderedBreach]


class TradeMonitorResult(TypedDict):
    items: list[TradeMonitorRow]


class TradeReviewReceipt(TypedDict):
    id: str
    state: ReviewState
    note: str


TRANSACTIONS = TypeAdapter(list[Annotated[TradeTransaction, WrapValidator(preserve_source_order)]])
METADATA: TypeAdapter[TradeMetadata] = TypeAdapter(
    Annotated[TradeMetadata, WrapValidator(preserve_source_order)]
)
TRADE_RISK = TypeAdapter(RecordedTradeRisk)
MONITOR_ROW: TypeAdapter[TradeMonitorRow] = TypeAdapter(
    Annotated[TradeMonitorRow, WrapValidator(preserve_source_order)]
)
REVIEW_RECEIPT = TypeAdapter(TradeReviewReceipt)
TRADE_TEXT: TypeAdapter[str | None] = TypeAdapter(str | None)
LEDGER_VALUATION = TypeAdapter(LedgerValuationInput)

# These duplicated context fields exist in historical ledger-created events.
LEGACY_CONTEXT_FIELDS = {
    "symbol",
    "external_reference",
    "source_file_id",
    "thesis_id",
    "strategy_id",
    "rationale",
}


def trade_risk_snapshot(value: object) -> SavedTradeSnapshot:
    if not value:
        return {"nav": "0", "beta": None, "positions": [], "exposures": {}}
    data = LEDGER_VALUATION.validate_python(value, strict=True)
    return {
        "nav": data["portfolio"]["nav"],
        "cash": data["portfolio"]["cash"],
        "beta": data["risk"].get("beta"),
        "gross_exposure": data["risk"].get("gross_exposure"),
        "positions": [{"symbol": p["symbol"], "weight": p["weight"]} for p in data["positions"]],
        "exposures": data["exposures"],
        "as_of": data["as_of"],
    }


def position_weight(snapshot: RecordedTradeRisk | None, symbol: str | None) -> Observation | None:
    if not snapshot or snapshot.get("nav") is None:
        return None
    return next(
        (row.get("weight") for row in snapshot.get("positions", []) if row["symbol"] == symbol),
        0,
    )


def sector_weight(snapshot: RecordedTradeRisk | None, sector: str | None) -> Observation | None:
    if not snapshot or snapshot.get("nav") is None or not sector:
        return None
    return next(
        (
            row.get("weight")
            for row in snapshot.get("exposures", {}).get("sector", [])
            if row["name"] == sector
        ),
        0,
    )
