"""Observe the existing local Compose project; never recreate configuration or data."""

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
SERVICES = (
    "postgres",
    "redis",
    "minio",
    "api",
    "worker-data",
    "worker-quant",
    "report-engine",
    "terminal-web",
    "prometheus",
    "grafana",
)
PROBES = {
    "api": ("http://127.0.0.1:8000/health/live", "http://127.0.0.1:8000/health/ready"),
    "report-engine": ("http://127.0.0.1:8010/health/ready",),
    "terminal-web": ("http://127.0.0.1:3001/login",),
    "prometheus": ("http://127.0.0.1:9090/api/v1/targets",),
    "grafana": ("http://127.0.0.1:3003/api/health",),
}


def command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=35,
        check=False,
        creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
    )


def probe(service: str, url: str) -> bool:
    try:
        with urlopen(url, timeout=8) as response:
            if response.status != 200:
                return False
            if service == "prometheus":
                payload = json.load(response)
                targets = payload["data"]["activeTargets"]
                required = {"knk-api", "knk-reports"}
                return required <= {
                    target["labels"].get("job") for target in targets if target["health"] == "up"
                }
            return True
    except Exception:
        return False


def cycle(env_file: str, failures: dict[str, int], restart: bool) -> list[dict[str, object]]:
    compose = ["docker", "compose", "--env-file", env_file]
    observed: list[dict[str, object]] = []
    try:
        result = command([*compose, "ps", "--all", "--format", "json"])
        if result.returncode:
            return [{"service": "docker", "state": "UNAVAILABLE", "action": "NONE"}]
        rows = [json.loads(line) for line in result.stdout.splitlines() if line.strip()]
        containers = {row["Service"]: row for row in rows}
    except (OSError, subprocess.TimeoutExpired, ValueError, KeyError):
        return [{"service": "docker", "state": "UNAVAILABLE", "action": "NONE"}]
    for service in SERVICES:
        row = containers.get(service, {})
        # Docker bounds its starting period; do not interrupt migrations or warmup.
        if row.get("State") == "running" and row.get("Health") == "starting":
            observed.append(
                {
                    "service": service,
                    "state": "STARTING",
                    "consecutive_failures": failures.get(service, 0),
                    "action": "NONE",
                }
            )
            continue
        container_healthy = row.get("State") == "running" and row.get("Health") == "healthy"
        healthy = container_healthy
        if healthy and service in PROBES:
            healthy = all(probe(service, url) for url in PROBES[service])
        upstream_failure = service == "prometheus" and container_healthy and not healthy
        action = "NONE"
        if healthy:
            failures[service] = 0
        else:
            failures[service] = min(3, failures.get(service, 0) + 1)
            if failures[service] >= 3:
                action = "MANUAL_ATTENTION"
            elif restart and not upstream_failure and row.get("State") in ("running", "exited"):
                try:
                    repaired = command([*compose, "restart", service])
                    action = "RESTART_REQUESTED" if repaired.returncode == 0 else "RESTART_FAILED"
                except (OSError, subprocess.TimeoutExpired):
                    action = "RESTART_FAILED"
        observed.append(
            {
                "service": service,
                "state": "HEALTHY"
                if healthy
                else "UPSTREAM_UNHEALTHY"
                if upstream_failure
                else "FAILED",
                "consecutive_failures": failures[service],
                "action": action,
            }
        )
    init = containers.get("minio-init", {})
    observed.append(
        {
            "service": "minio-init",
            "state": "SUCCEEDED"
            if init.get("State") == "exited" and init.get("ExitCode") == 0
            else "UNVERIFIED",
            "action": "NONE",
        }
    )
    return observed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env.compose.local")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--observe-only", action="store_true")
    args = parser.parse_args()
    logs = ROOT / "logs"
    logs.mkdir(exist_ok=True)
    state_path = logs / "overnight-watchdog-state.json"
    failures: dict[str, int] = {}
    if state_path.exists():
        persisted = json.loads(state_path.read_text())
        failures = {
            key: min(3, max(0, int(value))) for key, value in persisted.items() if key in SERVICES
        }
    while True:
        observations = cycle(args.env_file, failures, not args.observe_only)
        event = {"timestamp": datetime.now(UTC).isoformat(), "observations": observations}
        with (logs / "overnight-watchdog.jsonl").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event) + "\n")
        state_path.write_text(json.dumps(failures), encoding="utf-8")
        if args.once:
            print(json.dumps(event))
            return int(any(row["state"] not in ("HEALTHY", "SUCCEEDED") for row in observations))
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
