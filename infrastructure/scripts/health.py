from __future__ import annotations

import json
import time
import urllib.error
import urllib.request


def main() -> None:
    results = {}
    for service, url in {
        "api": "http://127.0.0.1:8000/health/ready",
        "terminal": "http://127.0.0.1:3001/login",
    }.items():
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = response.read(1000000)
                ready = response.status == 200 and (
                    json.loads(body).get("status") == "ready"
                    if service == "api"
                    else b"KnK" in body
                )
                results[service] = {
                    "state": "RESPONDING" if ready else "NOT_READY",
                    "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                }
        except (OSError, ValueError, urllib.error.URLError):
            results[service] = {"state": "OFFLINE", "latency_ms": None}
    print(json.dumps(results, indent=2))
    raise SystemExit(0 if all(row["state"] == "RESPONDING" for row in results.values()) else 1)


if __name__ == "__main__":
    main()
