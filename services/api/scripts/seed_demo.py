from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

API_ROOT = Path(__file__).resolve().parents[1]
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.database import SessionLocal, engine  # noqa: E402
from app.models import Base  # noqa: E402
from app.services import DemoIngestionService  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Seed deterministic KnK Capital demo data through the real ingestion pipeline."
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing records before loading deterministic demo data.",
    )
    args = parser.parse_args()
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        counts = DemoIngestionService(session).seed(reset=args.reset)
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
