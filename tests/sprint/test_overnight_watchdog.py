import json
import subprocess

from scripts import overnight_watchdog as watchdog


def test_watchdog_bounds_restarts_without_any_data_reset(monkeypatch):
    calls = []
    rows = [
        {"Service": name, "State": "running", "Health": "healthy"} for name in watchdog.SERVICES
    ]
    rows[3]["Health"] = "unhealthy"
    rows.append({"Service": "minio-init", "State": "exited", "ExitCode": 0})

    def command(args):
        calls.append(args)
        return subprocess.CompletedProcess(args, 0, "\n".join(json.dumps(row) for row in rows), "")

    monkeypatch.setattr(watchdog, "command", command)
    monkeypatch.setattr(watchdog, "probe", lambda *_: True)
    failures = {}
    for _ in range(5):
        result = watchdog.cycle(".env.compose.local", failures, True)
    assert len([call for call in calls if "restart" in call]) == 2
    assert all(call[-1] == "api" for call in calls if "restart" in call)
    assert next(row for row in result if row["service"] == "api")["action"] == "MANUAL_ATTENTION"
    assert not any(word in call for call in calls for word in ("down", "rm", "volume", "up"))


def test_docker_failure_never_invokes_repair(monkeypatch):
    calls = []

    def command(args):
        calls.append(args)
        return subprocess.CompletedProcess(args, 1, "", "unavailable")

    monkeypatch.setattr(watchdog, "command", command)
    assert watchdog.cycle(".env.compose.local", {}, True)[0]["state"] == "UNAVAILABLE"
    assert len(calls) == 1


def test_observe_only_does_not_restart(monkeypatch):
    monkeypatch.setattr(
        watchdog, "command", lambda args: subprocess.CompletedProcess(args, 0, "", "")
    )
    result = watchdog.cycle(".env.compose.local", {}, False)
    assert all(row["action"] == "NONE" for row in result)
