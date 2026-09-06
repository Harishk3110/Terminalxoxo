"""Local release measurements. Does not create ledger transactions or external files."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics
import time
from urllib.request import urlopen, Request

TABLES = ["portfolio_transactions", "transaction_details", "uploaded_files", "external_files",
          "datasets", "dataset_versions", "analysis_runs", "portfolio_valuation_runs"]


def inventory(path):
    with sqlite3.connect(path) as db:
        names = {r[0] for r in db.execute("select name from sqlite_master where type='table'")}
        result = {}
        for table in TABLES:
            if table not in names:
                continue
            columns = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
            rows = db.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()
            result[table] = {str(row[columns.index("id")]): hashlib.sha256(json.dumps(row, default=str).encode()).hexdigest() for row in rows}
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["backup", "inventory", "compare", "benchmark"])
    parser.add_argument("--database", default="knk_terminal.db")
    parser.add_argument("--output", required=True)
    parser.add_argument("--before")
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.command == "backup":
        if output.exists():
            raise ValueError("Backup destination already exists")
        with sqlite3.connect(args.database) as source, sqlite3.connect(output) as target:
            source.backup(target)
        print("Consistent SQLite backup:", output)
        return
    if args.command in {"inventory", "compare"}:
        result = inventory(args.database)
        if args.command == "compare":
            old = json.loads(Path(args.before).read_text())
            for table, rows in old.items():
                assert all(result.get(table, {}).get(key) == digest for key, digest in rows.items()), table + " changed or lost existing records"
            print("All captured immutable records retained.")
    else:
        result = {}
        for name, route, method in [
            ("warm_summary", "/api/v1/operations/portfolio", "GET"),
            ("overview", "/api/v1/terminal/portfolio", "GET"),
            ("recalculation", "/api/v1/operations/portfolio/recalculate", "POST"),
            ("risk", "/api/v1/risk/default", "GET"),
        ]:
            timings = []
            for _ in range(6):
                start = time.perf_counter()
                with urlopen(Request(args.url + route, data=b"{}" if method == "POST" else None, headers={"Content-Type":"application/json"}, method=method), timeout=60) as response:
                    payload = json.load(response)
                timings.append(round((time.perf_counter() - start) * 1000, 2))
            result[name] = {"first_ms":timings[0], "warm_median_ms":statistics.median(timings[1:]), "samples_ms":timings}
            if name == "warm_summary":
                result["portfolio"] = payload["portfolio"]
                result["reconciliation"] = payload["reconciliation"]
        with urlopen(args.url + "/api/v1/terminal/health", timeout=30) as response:
            result["health"] = json.load(response)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result if args.command == "benchmark" else {k:len(v) for k,v in result.items()}, indent=2))


if __name__ == "__main__":
    main()
