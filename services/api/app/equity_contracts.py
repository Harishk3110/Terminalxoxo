"""Validated equity evidence keeps source extensions and explicit missing values."""

import json
from typing import Annotated, Literal, NotRequired, TypedDict

from pydantic import (
    ConfigDict,
    JsonValue,
    TypeAdapter,
    ValidatorFunctionWrapHandler,
    WrapValidator,
    with_config,
)

from .price_sources import PriceProvenance

JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


def finite_object(value: object) -> dict[str, JsonValue]:
    result = JSON_OBJECT.validate_python(value, strict=True)
    # JsonValue accepts non-finite floats, including inside unknown source extensions.
    json.dumps(result, allow_nan=False)
    return result


def preserve_source_order(
    value: object, handler: ValidatorFunctionWrapHandler
) -> dict[str, JsonValue]:
    original = finite_object(value)
    validated = finite_object(handler(original))
    if original.keys() != validated.keys():
        raise ValueError("Financial validation cannot add or discard source fields")
    # Report tables turn dictionary order into row order and include it in their hashes.
    return {key: validated[key] for key in original}


class StatementSource(TypedDict):
    symbol: str
    unit: str
    source: str
    quality: str
    as_of: str | None
    items: list[dict[str, JsonValue]]


@with_config(ConfigDict(extra="allow", strict=True, allow_inf_nan=False))
class FinancialEvidence(StatementSource):
    warnings: NotRequired[list[str]]
    lineage: NotRequired[list[dict[str, JsonValue]]]


@with_config(ConfigDict(extra="allow", strict=True, allow_inf_nan=False))
class FinancialQuote(TypedDict, total=False):
    id: str
    symbol: str
    price: int | float | None
    as_of: str | None


OrderedFinancialQuote = Annotated[FinancialQuote, WrapValidator(preserve_source_order)]


@with_config(ConfigDict(extra="allow", strict=True, allow_inf_nan=False))
class FinancialReport(StatementSource):
    instrument_id: str
    currency: str
    frequency: str
    actual_estimate: str
    ratios: list[dict[str, JsonValue]]
    quote: OrderedFinancialQuote
    state: Literal["AVAILABLE", "INSUFFICIENT_DATA"]
    warnings: list[str]
    lineage: NotRequired[list[dict[str, JsonValue]]]


class SecurityQuote(TypedDict):
    bid: float | None
    ask: float | None
    open: float | None
    high: float | None
    low: float | None
    volume: float | None
    vwap: float | None
    last: float | None
    spread: float | None
    previous_close: float | None


class ProviderMapping(TypedDict):
    provider: str
    symbol: str


class SecuritySnapshot(TypedDict):
    symbol: str
    name: str
    sector: str | None
    industry: str | None
    country: str | None
    currency: str
    asset_class: str
    figi: str | None
    isin: str | None
    float: None
    description: None
    beta: None
    market_cap: float | None
    enterprise_value: float | None
    shares: float | None
    dividend_yield: float | None
    fifty_two_week_low: float | None
    fifty_two_week_high: float | None
    quote: SecurityQuote
    provenance: PriceProvenance
    financial_source: str | None
    financial_quality: str | None
    mappings: list[ProviderMapping]
    warnings: list[str]


FINANCIAL_EVIDENCE: TypeAdapter[FinancialEvidence] = TypeAdapter(
    Annotated[FinancialEvidence, WrapValidator(preserve_source_order)]
)
FINANCIAL_QUOTE: TypeAdapter[FinancialQuote] = TypeAdapter(OrderedFinancialQuote)
FINANCIAL_REPORT: TypeAdapter[FinancialReport] = TypeAdapter(
    Annotated[FinancialReport, WrapValidator(preserve_source_order)]
)
WARNINGS = TypeAdapter(list[str])
