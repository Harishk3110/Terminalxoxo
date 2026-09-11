from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Literal, TypedDict


class ServiceProbe(TypedDict):
    state: Literal["RESPONDING", "NOT_READY", "OFFLINE"]
    latency_ms: float | None


def main() -> None:
    results: dict[str, ServiceProbe] = {}
    for service, url in {
        "api": "http://127.0.0.1:8000/health/ready",
        "terminal": "http://127.0.0.1:3001/login",
    }.items():
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                body = response.read(1000000)
                if service == "api":
                    payload: object = json.loads(body)
                    ready = (
                        response.status == 200
                        and isinstance(payload, dict)
                        and payload.get("status") == "ready"
                    )
                else:
                    ready = response.status == 200 and b"KnK" in body
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
