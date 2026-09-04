from __future__ import annotations

import argparse
import time

import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

try:
    from prefect import flow, task
except Exception:  # pragma: no cover
    def flow(fn):
        return fn

    def task(fn):
        return fn


logger = structlog.get_logger()


@task
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=4))
def ingest_demo_prices() -> dict[str, str]:
    logger.info("demo_price_ingestion", provider="KnK deterministic fixture", quality="DEMO DATA")
    return {"dataset": "demo-equity-prices", "quality": "DEMO DATA", "state": "completed"}


@flow(name="knk-demo-data-maintenance")
def run_once() -> dict[str, str]:
    return ingest_demo_prices()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if not args.daemon:
        print(run_once())
        return
    while True:
        print(run_once())
        time.sleep(60)


if __name__ == "__main__":
    main()
