"""Compare preserved business records without printing private row contents."""

import argparse
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

TABLES = (
    "portfolio_transactions",
    "transaction_details",
    "dataset_versions",
    "analysis_runs",
    "research_notes",
    "investment_theses",
    "thesis_sources",
    "thesis_attachments",
    "portfolio_profiles",
    "portfolio_balance_adjustments",
)


def snapshot(path):
    with closing(
        sqlite3.connect(path.resolve(strict=True).as_uri() + "?mode=ro", uri=True)
    ) as database:
        available = {
            row[0] for row in database.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        result = {}
        for table in TABLES:
            if table not in available:
                continue
            rows = database.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()
            result[table] = {
                "rows": len(rows),
                "sha256": hashlib.sha256(
                    json.dumps(rows, sort_keys=True, default=str).encode()
                ).hexdigest(),
            }
        active = {
            table: database.execute(
                f"SELECT COUNT(*) FROM {table} WHERE status IN ('QUEUED','RUNNING')"
            ).fetchone()[0]
            for table in ("analysis_runs", "ingestion_jobs")
        }
        return {"tables": result, "active_jobs": active}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    parser.add_argument("--reference", type=Path)
    args = parser.parse_args()
    result = snapshot(args.database)
    if args.reference:
        reference = snapshot(args.reference)
        result["preserved"] = result["tables"] == reference["tables"]
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result.get("preserved", True) else 1)
