"""Typed views of the ledger and persisted broker inputs used for reconciliation."""

from typing import Annotated, Literal, NotRequired, TypedDict

from pydantic import AfterValidator, ConfigDict, JsonValue, TypeAdapter, WrapValidator, with_config

from .equity_contracts import preserve_source_order
from .portfolio_domain.money import decimal


def bounded_amount(value: str | int | float) -> str | int | float:
    decimal(value)
    return value


Amount = Annotated[str | int | float, AfterValidator(bounded_amount)]


class ReferencePortfolio(TypedDict):
    id: str
    nav: str | int | float | None


class CashAmount(TypedDict):
    currency: str
    amount: Amount | None


class PositionAmount(TypedDict):
    symbol: str
    quantity: NotRequired[Amount | None]
    average_cost: NotRequired[Amount | None]


class EffectiveTransaction(TypedDict):
    id: str
    quantity: NotRequired[Amount | None]
    price: NotRequired[Amount | None]
    commission: NotRequired[Amount | None]
    ledger_state: NotRequired[str]


class ReconciliationHeader(TypedDict):
    portfolio: ReferencePortfolio
    as_of: str


class ReconciliationBook(ReconciliationHeader):
    cash: list[CashAmount]
    positions: list[PositionAmount]
    transactions: list[EffectiveTransaction]


@with_config(ConfigDict(extra="allow", strict=True, allow_inf_nan=False))
class ReconciliationFill(TypedDict):
    execution_id: str
    quantity: Amount | None
    price: Amount | None
    commission: NotRequired[Amount | None]


OrderedFill = Annotated[ReconciliationFill, WrapValidator(preserve_source_order)]


class ReconciliationBroker(TypedDict):
    account_fingerprint: NotRequired[str | None]
    cash: NotRequired[list[CashAmount]]
    positions: NotRequired[list[PositionAmount]]
    fills: NotRequired[list[OrderedFill]]


BreakType = Literal[
    "NAV_MISMATCH",
    "CASH_MISMATCH",
    "QUANTITY_MISMATCH",
    "COST_BASIS_MISMATCH",
    "UNMATCHED_BROKER_FILL",
    "FILL_QUANTITY_MISMATCH",
    "FILL_PRICE_MISMATCH",
    "COMMISSION_MISMATCH",
]


class ReconciliationItem(TypedDict):
    type: BreakType
    key: str
    internal: JsonValue
    external: JsonValue
    difference: str | None
    severity: Literal["WARN"]
    snapshot_id: NotRequired[str]
    id: NotRequired[str]


class ReconciliationResult(TypedDict):
    state: Literal["BROKER_NOT_CONNECTED", "BREAKS", "MATCHED"]
    source: str
    items: list[ReconciliationItem]
    warnings: list[str]
    as_of: NotRequired[str]
    internal_nav: NotRequired[Amount | None]
    broker_as_of: NotRequired[str]
    internal_as_of: NotRequired[str]


HEADER = TypeAdapter(ReconciliationHeader)
BOOK = TypeAdapter(ReconciliationBook)
BROKER = TypeAdapter(ReconciliationBroker)
