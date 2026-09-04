from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic KnK Capital demo data.")
    parser.add_argument("--reset", action="store_true", help="Rewrite existing demo fixture snapshot.")
    args = parser.parse_args()
    target = Path("data/fixtures/demo-seed.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "brand": "KnK Capital",
        "environment": "local-demo",
        "base_currency": "SGD",
        "reference_capital": 70000,
        "quality": "DEMO DATA",
    }
    if target.exists() and not args.reset:
        print(f"Demo seed already exists: {target}")
        return
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
