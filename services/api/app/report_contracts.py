"""Validated rendering input. No renderer is allowed to query mutable market data."""

import hashlib
import json
from datetime import date
from typing import Literal, TypedDict

from pydantic import BaseModel, ConfigDict, Field, JsonValue

ReportKind = Literal[
    "portfolio", "risk", "backtest", "factor", "macro", "equity", "dcf", "comps", "quant"
]
ReportFormat = Literal["xlsx", "pptx", "pdf"]
Cell = str | int | float | bool | None
FORMATS: dict[str, tuple[str, ...]] = {
    "portfolio": ("xlsx", "pptx", "pdf"),
    "risk": ("xlsx", "pptx", "pdf"),
    "backtest": ("xlsx", "pdf"),
    "factor": ("xlsx",),
    "macro": ("xlsx",),
    "equity": ("xlsx", "pptx", "pdf"),
    "dcf": ("xlsx",),
    "comps": ("xlsx",),
    "quant": ("pptx",),
}
ANALYSIS_KINDS: dict[str, tuple[str, ...]] = {
    "backtest": ("backtest",),
    "factor": ("factor",),
    "dcf": ("dcf",),
    "comps": ("comparables",),
    # Keep the older persisted spelling readable alongside the worker's kind.
    "quant": ("backtest", "alpha", "factor", "model", "monte_carlo", "montecarlo"),
}


class ReportTemplate(TypedDict):
    kind: str
    formats: tuple[str, ...]
    analysis_kinds: tuple[str, ...]


class ReportTemplates(TypedDict):
    items: list[ReportTemplate]


CONTENT_TYPES = {
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
}


class ReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: ReportKind
    format: ReportFormat = "xlsx"
    portfolio: str = Field(default="KNK_MAIN", min_length=1, max_length=36)
    valuation_run_id: str | None = Field(default=None, max_length=36)
    as_of: date | None = None
    analysis_run_id: str | None = Field(default=None, max_length=36)
    symbol: str = Field(default="AAPL", min_length=1, max_length=32)


class ReportSection(BaseModel):
    title: str
    columns: list[str]
    rows: list[list[Cell]]


class ReportSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    kind: ReportKind
    requested_at: str
    data_as_of: str | None
    source: str
    quality: str
    currency: str
    calculation_version: str
    references: dict[str, JsonValue]
    sections: list[ReportSection]
    payload: dict[str, JsonValue]
    disclosure: str = "KnK Capital | Private internal research | Manual execution only"


def canonical(value: dict[str, JsonValue]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def digest(value: dict[str, JsonValue]) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def scalar(value: JsonValue) -> Cell:
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, allow_nan=False)
    return value


def section(title: str, value: JsonValue) -> ReportSection:
    if isinstance(value, list) and value and all(isinstance(row, dict) for row in value):
        records = [row for row in value if isinstance(row, dict)]
        columns = list(dict.fromkeys(key for row in records for key in row))
        rows = [[scalar(row.get(key)) for key in columns] for row in records]
    elif isinstance(value, dict):
        columns = ["Metric", "Value"]
        rows = [[key, scalar(item)] for key, item in value.items()]
    else:
        columns = ["Value"]
        rows = [[scalar(item)] for item in value] if isinstance(value, list) else [[scalar(value)]]
    return ReportSection(title=title, columns=columns, rows=rows)
