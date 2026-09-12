"""Curated fundamental statements; actual/estimate, units and versions remain distinct."""

import math
from dataclasses import dataclass, field
from decimal import Decimal, DecimalException
from typing import NotRequired, TypedDict

from pydantic import ConfigDict, JsonValue, TypeAdapter, with_config
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .data_mapping import header
from .equity_contracts import FINANCIAL_EVIDENCE, FinancialEvidence, finite_object
from .quant_data import dataset_rows

METRICS = {
    "revenue": "revenue",
    "sales": "revenue",
    "gross profit": "gross_profit",
    "ebit": "ebit",
    "operating income": "ebit",
    "net income": "net_income",
    "operating cash flow": "operating_cash_flow",
    "capex": "capex",
    "capital expenditures": "capex",
    "free cash flow": "free_cash_flow",
    "fcf": "free_cash_flow",
    "assets": "assets",
    "total assets": "assets",
    "debt": "debt",
    "total debt": "debt",
    "cash": "cash",
    "cash and equivalents": "cash",
    "shares": "shares",
    "shares outstanding": "shares",
}
METRICS.update(
    {
        name.replace("_", " "): name
        for name in (
            "ebitda",
            "depreciation",
            "interest_expense",
            "tax_expense",
            "dividends",
            "liabilities",
            "equity",
            "current_assets",
            "current_liabilities",
            "working_capital",
            "invested_capital",
        )
    }
)
METRICS.update(
    {
        "depreciation and amortization": "depreciation",
        "shareholders equity": "equity",
        "total liabilities": "liabilities",
    }
)


@with_config(ConfigDict(strict=True))
class ImportedRow(TypedDict):
    symbol: str
    period: str | int
    frequency: str
    actual_estimate: str
    report_date: str
    unit: str
    scale: str | int | float
    metric: NotRequired[str]
    value: NotRequired[JsonValue]
    metrics: NotRequired[dict[str, JsonValue] | None]


class MetricSource(TypedDict):
    version_id: str
    report_date: str
    unit: str
    scale: str


class StatementLineage(TypedDict):
    source: str
    version_id: str
    file_id: JsonValue
    licence: JsonValue


IMPORTED_ROW = TypeAdapter(ImportedRow)


@dataclass
class StatementPeriod:
    year: str
    frequency: str
    actual_estimate: str
    report_date: str
    dataset_version_id: str
    values: dict[str, float] = field(default_factory=dict)
    metric_sources: dict[str, MetricSource] = field(default_factory=dict)

    def payload(self) -> dict[str, JsonValue]:
        return {
            "year": self.year,
            "frequency": self.frequency,
            "actual_estimate": self.actual_estimate,
            "report_date": self.report_date,
            "dataset_version_id": self.dataset_version_id,
            "metric_sources": finite_object(self.metric_sources),
            **self.values,
        }


def scaled_metric(value: JsonValue, scale: str | int | float) -> float:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Fundamental value must be a finite numeric scalar")
    if isinstance(scale, bool):
        raise ValueError("Fundamental scale must be finite and positive")
    try:
        amount, multiplier = Decimal(str(value)), Decimal(str(scale))
        if not amount.is_finite() or not multiplier.is_finite() or multiplier <= 0:
            raise ValueError("Fundamental value must be finite and scale must be positive")
        # Preserve the established Decimal arithmetic and final float conversion.
        result = float(amount * multiplier / 1_000_000)
    except (DecimalException, OverflowError) as exc:
        raise ValueError("Fundamental value and scale must produce a finite amount") from exc
    if not math.isfinite(result):
        raise ValueError("Fundamental value and scale must produce a finite amount")
    return result


def curated_statements(session: Session, item: models.Instrument) -> FinancialEvidence | None:
    versions = session.execute(
        select(models.DatasetVersion, models.Dataset)
        .join(models.Dataset, models.Dataset.id == models.DatasetVersion.dataset_id)
        .where(models.Dataset.dataset_type.in_(["fundamentals_long", "fundamentals_wide"]))
        .order_by(models.DatasetVersion.created_at)
    ).all()
    statements: dict[tuple[str, str, str], StatementPeriod] = {}
    lineage: list[StatementLineage] = []
    warnings: list[str] = []
    for version, dataset in versions:
        schema = version.schema_json or {}
        if not schema.get("curated_key"):
            continue
        imported, _ = dataset_rows(session, version.id)
        for raw in imported:
            if raw.get("symbol") != item.symbol:
                continue
            row = IMPORTED_ROW.validate_python(raw, strict=True)
            key = (
                str(row["period"]),
                str(row["frequency"]).upper(),
                str(row["actual_estimate"]).upper(),
            )
            statement = statements.setdefault(
                key,
                StatementPeriod(*key, row["report_date"], version.id),
            )
            statement.report_date = max(statement.report_date, row["report_date"])
            metrics = row.get("metrics")
            if not metrics:
                if "metric" not in row or "value" not in row:
                    raise ValueError("Fundamental row requires metrics or a metric/value pair")
                metrics = {row["metric"]: row["value"]}
            for name, value in metrics.items():
                canonical = METRICS.get(header(name))
                if canonical:
                    unit = str(row["unit"]).upper()
                    if unit not in {item.currency, "CURRENCY", "SHARES"} or (
                        unit == "SHARES" and canonical != "shares"
                    ):
                        warnings.append(f"Excluded {canonical} in incompatible unit {unit}")
                        continue
                    statement.values[canonical] = scaled_metric(value, row["scale"])
                    statement.dataset_version_id = version.id
                    statement.metric_sources[canonical] = {
                        "version_id": version.id,
                        "report_date": row["report_date"],
                        "unit": unit,
                        "scale": str(row["scale"]),
                    }
            lineage.append(
                {
                    "source": dataset.source,
                    "version_id": version.id,
                    "file_id": schema.get("file_id"),
                    "licence": schema.get("licence"),
                }
            )
    if not statements:
        return None
    rows = sorted(statements.values(), key=lambda r: (r.year, r.frequency, r.actual_estimate))
    return FINANCIAL_EVIDENCE.validate_python(
        finite_object(
            {
                "symbol": item.symbol,
                "unit": f"{item.currency} millions / shares in millions",
                "source": " / ".join(sorted({r["source"] for r in lineage})),
                "quality": "FILE IMPORT",
                "as_of": max(r.report_date for r in rows),
                "items": [row.payload() for row in rows],
                "lineage": lineage,
                "warnings": sorted(set(warnings))
                + [
                    "Imported statements are user-provided, not independently verified filings; point-in-time availability is unverified.",
                    "Wide-format shares use the stated numeric scale as share counts, not currency. Quarterly rows must be standalone quarters, not cumulative year-to-date cash flows.",
                ],
            }
        ),
        strict=True,
    )
