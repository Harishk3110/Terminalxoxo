"""Durable, atomically claimed analytical and provider-check jobs. No user code."""

import argparse
import asyncio
import time
from datetime import UTC, datetime

import structlog
from sqlalchemy import select, update

from . import models
from .config import get_settings
from .database import SessionLocal
from .provider_data import NAMES, adapters, connection
from .provider_probe import probe
from .terminal_worker import execute_run
from .worker_health import dispatcher_state, heartbeat

logger = structlog.get_logger()


async def execute_provider_job(job_id):
    with SessionLocal() as session:
        result = session.execute(
            update(models.IngestionJob)
            .where(models.IngestionJob.id == job_id, models.IngestionJob.status == "QUEUED")
            .values(status="RUNNING", started_at=datetime.now(UTC), worker_id="data-dispatcher")
        )
        session.commit()
        if result.rowcount != 1:
            return
        job = session.get(models.IngestionJob, job_id)
        try:
            if job.job_type != "provider_health_check":
                raise ValueError(
                    "Unsupported queued data job; approved data imports use the private API"
                )
            outcomes = []
            settings = get_settings()
            instances = adapters(settings)
            for key in NAMES:
                row = connection(session, key, settings)
                if row.enabled and row.configured and row.connection_state != "REVOKED":
                    outcome = await probe(
                        session,
                        row,
                        key,
                        instances[key],
                        (job.parameters or {}).get("actor_id"),
                        job.correlation_id,
                    )
                    outcomes.append(
                        {"provider": row.provider_name, "state": outcome["connection_state"]}
                    )
            job.records_received = len(outcomes)
            job.records_accepted = sum(row["state"] == "CONNECTED" for row in outcomes)
            job.records_rejected = len(outcomes) - job.records_accepted
            job.status = "FAILED" if job.records_rejected else "SUCCEEDED"
            job.error_message = (
                "One or more connection probes failed" if job.records_rejected else None
            )
            session.add(
                models.IngestionJobRun(
                    job_id=job.id,
                    state=job.status,
                    message="Observed configured provider responses"
                    if outcomes
                    else "No enabled configured providers; zero probes performed",
                    log_payload={"items": outcomes},
                )
            )
        except Exception as exc:
            session.rollback()
            job = session.get(models.IngestionJob, job_id)
            job.status, job.error_category = "FAILED", type(exc).__name__
            job.error_message = "Data job failed; inspect private provider status and configuration"
        job.finished_at, job.progress = datetime.now(UTC), 1
        session.commit()


def run_once(kind):
    model = models.IngestionJob if kind == "data" else models.AnalysisRun
    with SessionLocal() as session:
        statement = (
            select(model.id).where(model.status == "QUEUED").order_by(model.created_at).limit(1)
        )
        identifier = session.scalar(statement)
    if not identifier:
        return {"state": "NO_QUEUED_JOBS"}
    if kind == "data":
        asyncio.run(execute_provider_job(identifier))
    else:
        execute_run(identifier)
    return {"state": "JOB_HANDLED", "id": identifier}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", choices=["data", "quant"], required=True)
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    if args.healthcheck:
        with SessionLocal() as session:
            state = dispatcher_state(session, args.kind)
        print(state)
        raise SystemExit(0 if state["state"] == "RUNNING" else 1)
    with heartbeat(args.kind + "-dispatcher"):
        while True:
            try:
                result = run_once(args.kind)
                if not args.daemon:
                    print(result)
                    return
            except Exception as exc:
                if not args.daemon:
                    raise
                logger.error("queue_poll_failed", kind=args.kind, category=type(exc).__name__)
            time.sleep(3)


if __name__ == "__main__":
    main()
