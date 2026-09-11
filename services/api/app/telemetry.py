"""Bounded labels: resource identifiers and unmatched URLs never become metrics."""

import uuid
from collections.abc import Mapping


def request_id(value: str | None) -> str:
    try:
        return str(uuid.UUID(value)) if value and len(value) <= 36 else str(uuid.uuid4())
    except ValueError:
        return str(uuid.uuid4())


def metric_path(scope: Mapping[str, object], rejected: bool = False) -> str:
    if rejected:
        return "AUTH_REJECTED"
    template = getattr(scope.get("route"), "path", None)
    return template if isinstance(template, str) else "UNMATCHED"


JOB_STATES = ("PENDING", "QUEUED", "RUNNING", "RETRYING", "SUCCEEDED", "FAILED", "CANCELLED")
