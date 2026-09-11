"""Internal report dispatcher. Public health only; all report access is via the API."""

import threading
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from prometheus_client import CollectorRegistry, Gauge, generate_latest
from sqlalchemy import func, select, text

from .database import SessionLocal
from .object_storage import ObjectStorage
from .report_jobs import run_once
from .report_models import ReportJob
from .worker_health import heartbeat

last_poll = 0.0
poll_started = 0.0
stop = threading.Event()


def dispatch() -> None:
    global last_poll, poll_started
    with heartbeat("report-dispatcher"):
        while not stop.is_set():
            try:
                poll_started = time.monotonic()
                run_once()
                last_poll = time.monotonic()
            except Exception:
                # Do not expose database credentials through probe responses or logs.
                last_poll = 0
            finally:
                poll_started = 0
            stop.wait(3)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    stop.clear()
    thread = threading.Thread(target=dispatch, daemon=True)
    thread.start()
    yield
    stop.set()
    thread.join(timeout=30)


app = FastAPI(title="KnK private report worker", lifespan=lifespan, docs_url=None, redoc_url=None)


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"service": "report-engine", "state": "LIVE"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        storage = ObjectStorage()
        storage.put_bytes(
            key="health/report-worker.txt", data=b"report-worker", content_type="text/plain"
        )
        if storage.get_bytes("health/report-worker.txt") != b"report-worker":
            raise OSError("Readback mismatch")
        if not dispatcher_ready():
            raise OSError("Dispatcher has no recent successful poll")
    except Exception as exc:
        raise HTTPException(503, "Report dispatcher or dependencies are unavailable") from exc
    return {"service": "report-engine", "state": "READY"}


def dispatcher_ready() -> bool:
    now = time.monotonic()
    return bool(
        (last_poll and now - last_poll <= 60) or (poll_started and now - poll_started <= 900)
    )


@app.get("/metrics")
def metrics() -> Response:
    registry = CollectorRegistry()
    jobs = Gauge("knk_report_jobs", "Persisted report jobs", ["state"], registry=registry)
    worker = Gauge("knk_report_dispatcher_ready", "Recent successful queue poll", registry=registry)
    worker.set(int(dispatcher_ready()))
    with SessionLocal() as session:
        counts = {
            status: count
            for status, count in session.execute(
                select(ReportJob.status, func.count()).group_by(ReportJob.status)
            ).all()
        }
        for state in ("QUEUED", "RUNNING", "SUCCEEDED", "FAILED"):
            jobs.labels(state).set(counts.get(state, 0))
    return Response(generate_latest(registry), media_type="text/plain; version=0.0.4")
