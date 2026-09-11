import uuid
from types import SimpleNamespace

from app.telemetry import metric_path, request_id


def test_metrics_use_route_template_not_arbitrary_ids_or_unmatched_urls():
    scope = {
        "route": SimpleNamespace(path="/api/v1/instruments/{instrument_id}"),
        "path": "/api/v1/instruments/private-record",
    }
    assert metric_path(scope) == "/api/v1/instruments/{instrument_id}"
    assert metric_path({"path": "/attacker-controlled-label"}) == "UNMATCHED"
    assert metric_path(scope, rejected=True) == "AUTH_REJECTED"


def test_correlation_id_accepts_only_bounded_uuid():
    value = str(uuid.uuid4())
    assert request_id(value) == value
    for candidate in ("bearer-secret", "x" * 100000, "../../path", "\nlog injection", None):
        assert str(uuid.UUID(request_id(candidate))) != candidate
