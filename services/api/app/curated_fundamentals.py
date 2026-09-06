"""Curated fundamental statements; actual/estimate, units and versions remain distinct."""

import hashlib
import json
from decimal import Decimal

from sqlalchemy import select

from . import models
from .data_mapping import header
from .object_storage import ObjectStorage

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


def curated_statements(session, item):
    versions = session.execute(
        select(models.DatasetVersion, models.Dataset)
        .join(models.Dataset, models.Dataset.id == models.DatasetVersion.dataset_id)
        .where(models.Dataset.dataset_type.in_(["fundamentals_long", "fundamentals_wide"]))
        .order_by(models.DatasetVersion.created_at)
    ).all()
    statements, lineage, warnings = {}, [], []
    for version, dataset in versions:
        schema = version.schema_json or {}
        if not schema.get("curated_key"):
            continue
        content = ObjectStorage().get_bytes(schema["curated_key"])
        if hashlib.sha256(content).hexdigest() != schema["curated_hash"]:
            raise ValueError("Curated fundamental integrity check failed")
        for row in json.loads(content):
            if row.get("symbol") != item.symbol:
                continue
            key = (
                str(row["period"]),
                str(row["frequency"]).upper(),
                str(row["actual_estimate"]).upper(),
            )
            statement = statements.setdefault(
                key,
                {
                    "year": key[0],
                    "frequency": key[1],
                    "actual_estimate": key[2],
                    "report_date": row["report_date"],
                    "dataset_version_id": version.id,
                    "metric_sources": {},
                },
            )
            statement["report_date"] = max(statement["report_date"], row["report_date"])
            metrics = row.get("metrics") or {row["metric"]: row["value"]}
            for name, value in metrics.items():
                canonical = METRICS.get(header(name))
                if canonical:
                    unit = str(row["unit"]).upper()
                    if unit not in {item.currency, "CURRENCY", "SHARES"} or (
                        unit == "SHARES" and canonical != "shares"
                    ):
                        warnings.append(f"Excluded {canonical} in incompatible unit {unit}")
                        continue
                    statement[canonical] = float(
                        Decimal(str(value)) * Decimal(str(row["scale"])) / 1_000_000
                    )
                    statement["dataset_version_id"] = version.id
                    statement["metric_sources"][canonical] = {
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
    rows = sorted(
        statements.values(), key=lambda r: (r["year"], r["frequency"], r["actual_estimate"])
    )
    return {
        "symbol": item.symbol,
        "unit": f"{item.currency} millions / shares in millions",
        "source": " / ".join(sorted({r["source"] for r in lineage})),
        "quality": "FILE IMPORT",
        "as_of": max(r["report_date"] for r in rows),
        "items": rows,
        "lineage": lineage,
        "warnings": sorted(set(warnings))
        + [
            "Imported statements are user-provided, not independently verified filings; point-in-time availability is unverified.",
            "Wide-format shares use the stated numeric scale as share counts, not currency. Quarterly rows must be standalone quarters, not cumulative year-to-date cash flows.",
        ],
    }
