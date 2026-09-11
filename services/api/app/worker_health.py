"""Observed, expiring process heartbeats; job state alone is not worker health."""

import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Literal, TypedDict

from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .database import SessionLocal
from .price_sources import utc


class WorkerState(TypedDict):
    state: Literal["RUNNING", "OFFLINE", "NO_ACTIVE_RUNS", "UNVERIFIED"]
    as_of: str | datetime | None
    detail: str


def record_heartbeat(
    component: str, state: str, details: dict[str, JsonValue] | None = None
) -> None:
    with SessionLocal() as session:
        row = session.scalar(
            select(models.SystemHealthSnapshot)
            .where(models.SystemHealthSnapshot.component == component)
            .order_by(models.SystemHealthSnapshot.checked_at.desc())
            .limit(1)
        )
        if row is None:
            row = models.SystemHealthSnapshot(component=component, state=state)
            session.add(row)
        row.state, row.details, row.checked_at = state, details or {}, datetime.now(UTC)
        session.commit()


@contextmanager
def heartbeat(run_id: str) -> Iterator[None]:
    stop = threading.Event()
    component = "analytical-worker:" + run_id

    def beat() -> None:
        try:
            record_heartbeat(component, "RUNNING", {"run_id": run_id})
        except Exception:
            # A failed write must not interrupt research or fabricate a healthy state.
            pass

    def loop() -> None:
        while not stop.wait(15):
            beat()

    beat()
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join(timeout=5)
        try:
            record_heartbeat(component, "STOPPED", {"run_id": run_id})
        except Exception:
            pass


def dispatcher_state(session: Session, kind: str) -> WorkerState:
    row = session.scalar(
        select(models.SystemHealthSnapshot)
        .where(models.SystemHealthSnapshot.component == "analytical-worker:" + kind + "-dispatcher")
        .order_by(models.SystemHealthSnapshot.checked_at.desc())
        .limit(1)
    )
    fresh = (
        row
        and row.state == "RUNNING"
        and 0 <= (datetime.now(UTC) - utc(row.checked_at)).total_seconds() < 60
    )
    return {
        "state": "RUNNING" if fresh else "OFFLINE",
        "as_of": utc(row.checked_at).isoformat() if row else None,
        "detail": "SQL queue dispatcher; process heartbeat expires after 60s",
    }


def worker_state(session: Session, runs: Sequence[models.AnalysisRun]) -> WorkerState:
    if not runs:
        return {
            "state": "NO_ACTIVE_RUNS",
            "as_of": datetime.now(UTC).isoformat(),
            "detail": "On-demand processes; no active analytical runs",
        }
    observed = []
    for run in runs:
        row = session.scalar(
            select(models.SystemHealthSnapshot)
            .where(models.SystemHealthSnapshot.component == "analytical-worker:" + run.id)
            .order_by(models.SystemHealthSnapshot.checked_at.desc())
            .limit(1)
        )
        if (
            row
            and row.state == "RUNNING"
            and 0 <= (datetime.now(UTC) - utc(row.checked_at)).total_seconds() < 60
        ):
            observed.append(row)
    return {
        "state": "RUNNING" if len(observed) == len(runs) else "UNVERIFIED",
        "as_of": max((utc(row.checked_at) for row in observed), default=None),
        "detail": f"{len(observed)}/{len(runs)} active jobs have a process heartbeat within 60s",
    }
