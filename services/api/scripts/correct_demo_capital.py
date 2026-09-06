"""Back up SQLite and apply only the guarded managed-demo capital correction."""

import argparse
import hashlib
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import models  # noqa: E402
from app.portfolio_seed import profile_for, upgrade_demo_capital  # noqa: E402
from app.portfolio_valuation import PortfolioValuationService  # noqa: E402


def fingerprint(connection, table):
    # Only allow the explicit canonical tables, never user-supplied SQL identifiers.
    if table not in {
        "portfolio_transactions",
        "transaction_details",
        "portfolio_valuation_runs",
        "analysis_runs",
    }:
        raise ValueError("Unsupported preservation table")
    rows = connection.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()
    return len(rows), hashlib.sha256(json.dumps(rows, default=str).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("database", type=Path)
    parser.add_argument("backup", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    database, backup = args.database.resolve(strict=True), args.backup.resolve()
    if database == backup or backup.exists():
        raise ValueError("Backup must be a new path distinct from the source")
    tables = (
        "portfolio_transactions",
        "transaction_details",
        "portfolio_valuation_runs",
        "analysis_runs",
    )
    with sqlite3.connect(database) as source, sqlite3.connect(backup) as target:
        source.backup(target)
        if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Backup integrity check failed")
        before = {table: fingerprint(source, table) for table in tables}
        assert before == {table: fingerprint(target, table) for table in tables}
    engine = create_engine(f"sqlite:///{database.as_posix()}")
    with Session(engine) as session:
        profile = profile_for(session)
        if profile is None:
            raise ValueError("No KNK_MAIN ledger exists; no seed was created")
        portfolio = session.get(models.Portfolio, profile.portfolio_id)
        changed = upgrade_demo_capital(session, portfolio, profile)
        if args.apply:
            session.commit()
        else:
            session.rollback()
        result = PortfolioValuationService(session).calculate(end=date(2026, 9, 4))
    with sqlite3.connect(database) as source:
        after = {table: fingerprint(source, table) for table in tables}
    if before != after:
        raise RuntimeError("Canonical ledger or existing saved-run preservation check failed")
    print(
        json.dumps(
            {
                "applied": args.apply and changed,
                "would_change": changed,
                "backup": str(backup),
                "canonical_records_unchanged": before == after,
                "records": {key: value[0] for key, value in before.items()},
                "nav": result["portfolio"]["nav"],
                "opening_capital": result["portfolio"]["opening_capital"],
                "reconciliation": result["reconciliation"]["state"],
            },
            indent=2,
        )
    )
    engine.dispose()


if __name__ == "__main__":
    main()
