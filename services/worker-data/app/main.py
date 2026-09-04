from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone

import redis
import structlog
from sqlalchemy import create_engine, text
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from prefect import flow, task
except Exception:  # pragma: no cover
    def flow(fn):
        return fn

    def task(fn):
        return fn


logger = structlog.get_logger()
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./knk_terminal.db")


@task
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def ingest_demo_prices() -> dict[str, str]:
    logger.info("demo_price_ingestion", provider="KnK deterministic fixture", quality="DEMO DATA")
    return {"dataset": "demo-equity-prices", "quality": "DEMO DATA", "state": "completed"}


@flow(name="knk-demo-data-maintenance")
def run_once() -> dict[str, str]:
    return ingest_demo_prices()


def mark_job(job_id: str, status: str, progress: float, message: str | None = None) -> None:
    engine = create_engine(DATABASE_URL, future=True)
    now = datetime.now(timezone.utc)
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                update ingestion_jobs
                   set status = :status,
                       progress = :progress,
                       started_at = coalesce(started_at, :now),
                       finished_at = case when :status in ('SUCCEEDED', 'FAILED', 'CANCELLED') then :now else finished_at end,
                       error_message = :message,
                       updated_at = :now
                 where id = :job_id
                """
            ),
            {"status": status, "progress": progress, "message": message, "job_id": job_id, "now": now},
        )


def worker_loop() -> None:
    client = redis.Redis.from_url(REDIS_URL, socket_timeout=5)
    logger.info("worker_data_started", redis_url=REDIS_URL)
    while True:
        item = client.brpop("knk:jobs", timeout=10)
        if not item:
            continue
        _, payload = item
        job_id = payload.decode("utf-8")
        try:
            mark_job(job_id, "RUNNING", 0.25)
            time.sleep(0.2)
            mark_job(job_id, "SUCCEEDED", 1.0)
            logger.info("job_completed", job_id=job_id)
        except Exception as exc:  # noqa: BLE001
            mark_job(job_id, "FAILED", 1.0, str(exc))
            logger.exception("job_failed", job_id=job_id)


def healthcheck() -> None:
    redis.Redis.from_url(REDIS_URL, socket_timeout=3).ping()
    engine = create_engine(DATABASE_URL, future=True)
    with engine.connect() as connection:
        connection.execute(text("select 1"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    if args.healthcheck:
        healthcheck()
        print("ok")
        return
    if args.daemon:
        worker_loop()
        return
    print(run_once())


if __name__ == "__main__":
    main()
