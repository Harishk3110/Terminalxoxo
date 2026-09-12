"""Atomic state and evidence transitions for persisted analytical runs."""

from datetime import UTC, datetime
from typing import Literal

from pydantic import JsonValue
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from . import models

AnalysisState = Literal["RUNNING", "SUCCEEDED", "FAILED", "CANCELLED"]
PREDECESSORS: dict[AnalysisState, tuple[str, ...]] = {
    "RUNNING": ("QUEUED",),
    "SUCCEEDED": ("RUNNING",),
    "FAILED": ("QUEUED", "RUNNING"),
    "CANCELLED": ("QUEUED", "RUNNING"),
}
MESSAGES: dict[AnalysisState, str] = {
    "RUNNING": "Validated template executing in isolated process",
    "SUCCEEDED": "Result persisted",
    "FAILED": "Analysis failed",
    "CANCELLED": "Cancellation requested; worker result will be discarded",
}


def transition_run(
    session: Session,
    run_id: str,
    state: AnalysisState,
    *,
    result: dict[str, JsonValue] | None = None,
    error: str | None = None,
    expected_status: Literal["QUEUED", "RUNNING"] | None = None,
) -> bool:
    """Stage a transition; the caller commits its accompanying work and audit."""
    observed = session.execute(
        select(models.AnalysisRun.status, models.AnalysisRun.history).where(
            models.AnalysisRun.id == run_id
        )
    ).one_or_none()
    if observed is None:
        return False
    observed_state, observed_history = observed._t
    if observed_state not in PREDECESSORS[state] or (
        expected_status is not None and observed_state != expected_status
    ):
        return False
    now = datetime.now(UTC)
    history: list[dict[str, JsonValue]] = [
        *observed_history,
        {"state": state, "at": now.isoformat(), "message": error or MESSAGES[state]},
    ]
    # Match the exact observed state so a competing claim cannot lose its history.
    statement = (
        update(models.AnalysisRun)
        .where(models.AnalysisRun.id == run_id, models.AnalysisRun.status == observed_state)
        .values(status=state, history=history)
        .execution_options(synchronize_session=False)
        .returning(models.AnalysisRun.id)
    )
    if state == "RUNNING":
        statement = statement.values(started_at=now)
    else:
        statement = statement.values(
            finished_at=now,
            result=result if state == "SUCCEEDED" else None,
            error=error if state == "FAILED" else None,
        )
    return session.execute(statement).scalar_one_or_none() is not None
