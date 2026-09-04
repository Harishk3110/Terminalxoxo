from __future__ import annotations

import argparse
import math
import os
import time

import numpy as np
import structlog
from sqlalchemy import create_engine, text

logger = structlog.get_logger()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./knk_terminal.db")


def run_demo_backtest() -> dict[str, float | str]:
    equity = np.array([70000, 69250, 70640, 72120, 71380, 72840, 71482.35], dtype=float)
    returns = np.diff(equity) / equity[:-1]
    volatility = float(np.std(returns, ddof=1) * math.sqrt(252))
    logger.info("demo_backtest_completed", quality="DEMO DATA", volatility=volatility)
    return {"strategy": "quality_momentum_demo", "quality": "DEMO DATA", "annualized_volatility": volatility}


def healthcheck() -> None:
    engine = create_engine(DATABASE_URL, future=True)
    with engine.connect() as connection:
        connection.execute(text("select 1"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    if args.healthcheck:
        healthcheck()
        print("ok")
        return
    if not args.daemon:
        print(run_demo_backtest())
        return
    while True:
        print(run_demo_backtest())
        time.sleep(90)


if __name__ == "__main__":
    main()
