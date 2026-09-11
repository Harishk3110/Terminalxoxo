"""Local release measurements. Does not create ledger transactions or external files."""

import argparse
import hashlib
import json
import sqlite3
import statistics
import time
from contextlib import closing
from pathlib import Path
from urllib.request import Request, urlopen

TABLES = [
    "portfolio_transactions",
    "transaction_details",
    "uploaded_files",
    "external_files",
    "datasets",
    "dataset_versions",
    "analysis_runs",
    "portfolio_valuation_runs",
]


type RecordInventory = dict[str, dict[str, str]]


def inventory(path: Path) -> RecordInventory:
    with closing(sqlite3.connect(path.resolve(strict=True).as_uri() + "?mode=ro", uri=True)) as db:
        names = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
        result: RecordInventory = {}
        for table in TABLES:
            if table not in names:
                continue
            columns = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
            rows = db.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()
            result[table] = {
                str(row[columns.index("id")]): hashlib.sha256(
                    json.dumps(row, default=str).encode()
                ).hexdigest()
                for row in rows
            }
        if not result:
            raise ValueError("No business tables found in release database")
        return result


def compare_inventory(previous: object, current: RecordInventory) -> None:
    if not isinstance(previous, dict) or not previous:
        raise ValueError("Missing reference business inventory")
    for table, rows in previous.items():
        if table not in TABLES or not isinstance(rows, dict):
            raise ValueError("Invalid reference business inventory")
        if table not in current:
            raise ValueError(f"{table} changed or lost existing records")
        for key, digest in rows.items():
            if (
                not isinstance(key, str)
                or not key
                or not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise ValueError("Invalid reference business inventory")
            if current[table].get(key) != digest:
                raise ValueError(f"{table} changed or lost existing records")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["backup", "inventory", "compare", "benchmark"])
    parser.add_argument("--database", type=Path, default=Path("knk_terminal.db"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--before")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    output = Path(args.output)
    if args.command != "benchmark" and (
        output.resolve() == args.database.resolve()
        or (output.exists() and args.database.exists() and output.samefile(args.database))
    ):
        raise ValueError("Output must not overwrite the source database")
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "backup":
        if output.exists():
            raise ValueError("Backup destination already exists")
        source_path = args.database.resolve(strict=True)
        output.touch(exist_ok=False)
        with (
            closing(sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True)) as source,
            closing(sqlite3.connect(output)) as target,
        ):
            source.backup(target)
        print("Consistent SQLite backup:", output)
        return
    output_data: object
    summary: object
    if args.command in {"inventory", "compare"}:
        records = inventory(args.database)
        if args.command == "compare":
            if not args.before:
                raise ValueError("Reference inventory is required")
            compare_inventory(json.loads(Path(args.before).read_text()), records)
            print("All captured immutable records retained.")
        output_data = records
        summary = {key: len(rows) for key, rows in records.items()}
    else:
        result: dict[str, object] = {}
        for name, route, method in [
            ("warm_summary", "/api/v1/operations/portfolio", "GET"),
            ("overview", "/api/v1/terminal/portfolio", "GET"),
            ("recalculation", "/api/v1/operations/portfolio/recalculate", "POST"),
            ("risk", "/api/v1/risk/default", "GET"),
        ]:
            timings = []
            for _ in range(6):
                start = time.perf_counter()
                with urlopen(
                    Request(
                        args.url + route,
                        data=b"{}" if method == "POST" else None,
                        headers={"Content-Type": "application/json"},
                        method=method,
                    ),
                    timeout=60,
                ) as response:
                    payload: object = json.load(response)
                timings.append(round((time.perf_counter() - start) * 1000, 2))
            result[name] = {
                "first_ms": timings[0],
                "warm_median_ms": statistics.median(timings[1:]),
                "samples_ms": timings,
            }
            if name == "warm_summary":
                if (
                    not isinstance(payload, dict)
                    or not {"portfolio", "reconciliation"} <= payload.keys()
                ):
                    raise ValueError("Invalid portfolio benchmark response")
                result["portfolio"] = payload["portfolio"]
                result["reconciliation"] = payload["reconciliation"]
        with urlopen(args.url + "/api/v1/terminal/health", timeout=30) as response:
            result["health"] = json.load(response)
        output_data = summary = result
    output.write_text(json.dumps(output_data, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
