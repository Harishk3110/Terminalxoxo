"""Pine research evidence; observed signals do not establish fill equivalence."""

from typing import Literal, TypedDict

from pydantic import JsonValue

type PineStrategy = Literal["SMA", "RSI", "MACD", "BREAKOUT"]


class PineTemplate(TypedDict):
    source: str
    source_hash: str
    settings: dict[str, JsonValue]
    version: str
    language: Literal["Pine Script v6"]
    compatibility: Literal["PARTIALLY_SUPPORTED"]
    compilation: Literal["UNVERIFIED"]
    comparison: Literal["NOT_COMPARED"]
    quality: Literal["RESEARCH TEMPLATE"]
    as_of: None
    warnings: list[str]


class SavedPineTemplate(PineTemplate):
    pine_source: str


class SignalComparison(TypedDict):
    time: str
    close: float
    knk: int
    tradingview: int
    match: bool


class PineComparison(TypedDict):
    state: Literal["MISMATCHES", "MATCHED_OBSERVED_BARS"]
    source: str
    quality: str
    as_of: str
    source_hash: str
    row_count: int
    compared: int
    warmup_excluded: int
    missing_signals: int
    mismatch_count: int
    match_rate: float
    mismatches: list[SignalComparison]
    items: list[SignalComparison]
    warnings: list[str]
