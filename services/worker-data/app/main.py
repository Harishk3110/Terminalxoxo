"""Compatibility launcher for the API-owned durable data queue."""

import sys
from pathlib import Path

if __name__ == "__main__":
    api = Path(__file__).resolve().parents[2] / "api"
    if not api.is_dir():
        raise SystemExit("Build the API service image and run app.queue_worker --kind data")
    sys.path.insert(0, str(api))
    from app.queue_worker import main

    sys.argv[1:1] = ["--kind", "data"]
    main()
