"""Isolated worker for approved analytical templates; never evaluates user code."""

from __future__ import annotations

import sys
from collections.abc import Mapping

import pandas as pd
from pydantic import JsonValue
from sqlalchemy.orm import Session

from . import models
from .analysis_lifecycle import transition_run
from .database import SessionLocal
from .terminal_analytics import stress_result
from .valuation_values import jsonable


def backtest_result(session: Session, params: Mapping[str, JsonValue]) -> dict[str, JsonValue]:
    from .backtest_engine import BacktestSettings, simulate
    from .backtest_inputs import PinnedBacktestInputs, pin_backtest_inputs
    from .quant_data import dataset_rows
    from .research_inputs import bars_frame

    params = dict(params) if params.get("_datasets") else pin_backtest_inputs(session, params)
    pinned = PinnedBacktestInputs.model_validate(params)
    frames: dict[str, pd.DataFrame] = {}
    for symbol, evidence in pinned.datasets.items():
        rows, verified = dataset_rows(session, evidence["dataset_version_id"])
        if verified["content_hash"] != evidence["content_hash"]:
            raise ValueError("Pinned research input hash changed")
        frame = bars_frame(rows, symbol, pinned.start, pinned.end)
        fixing = pd.Series(
            {pd.Timestamp(day): float(row.rate) for day, row in pinned.fx[symbol].items()}
        ).reindex(frame.index)
        if fixing.isna().any():
            raise ValueError("Pinned prior-published FX fixing is incomplete")
        frame[["open", "high", "low", "close"]] = frame[["open", "high", "low", "close"]].mul(
            fixing, axis=0
        )
        frames[symbol] = frame
    settings = BacktestSettings.model_validate(
        {key: params[key] for key in BacktestSettings.model_fields if key in params}
    )
    result = simulate(frames, settings, sectors=pinned.sectors)
    gross = simulate(
        frames,
        settings.model_copy(
            update={"fee_bps": 0, "spread_bps": 0, "slippage_bps": 0, "short_borrow_rate": 0}
        ),
        sectors=pinned.sectors,
    )
    result["metrics"]["cost_drag"] = (
        gross["metrics"]["total_return"] - result["metrics"]["total_return"]
    )
    result["warnings"].append(
        "Gross is a separate zero-cost counterfactual; cash, integer sizing and rejected orders can differ. Cost drag is not identical to recorded commissions."
    )
    input_evidence = list(pinned.datasets.values())
    quality = {item["quality"] for item in input_evidence}
    result["warnings"].append(
        "FX assumption: each full bar uses its last available fixing published before that UTC date. Fills and marks use that same fixing, not contemporaneous intraday FX. Cash is held in the base currency."
    )
    return jsonable(
        {
            **result,
            "gross_equity_curve": gross["equity_curve"],
            "inputs": params["_datasets"],
            "currency": pinned.base_currency,
            "fx": params["_fx"],
            "source": " / ".join(dict.fromkeys(item["source"] for item in input_evidence)),
            "quality": next(iter(quality)) if len(quality) == 1 else "MIXED SOURCES",
            "as_of": pd.Timestamp(next(iter(frames.values())).index[-1]).isoformat(),
            "parameters": {key: value for key, value in params.items() if not key.startswith("_")},
        }
    )


def execute_run(run_id: str) -> None:
    from .worker_health import heartbeat

    with SessionLocal() as session:
        claimed = transition_run(session, run_id, "RUNNING")
        session.commit()
        if not claimed:
            return
    with heartbeat(run_id):
        _execute_run(run_id)


def _execute_run(run_id: str) -> None:
    with SessionLocal() as session:
        run = session.get(models.AnalysisRun, run_id)
        if not run or run.status != "RUNNING":
            return
        try:
            if run.kind == "stress":
                result = stress_result(session, run.parameters)
            elif run.kind == "backtest":
                result = backtest_result(session, run.parameters)
            elif run.kind == "model":
                from .model_runs import model_result

                result = model_result(session, run.parameters, run.id)
            elif run.kind == "monte_carlo":
                from .monte_carlo import monte_carlo_result

                result = monte_carlo_result(run.parameters)
            else:
                raise ValueError("Unknown approved analytical template")
            validated = jsonable(result)
            if not isinstance(validated, dict):
                raise ValueError("Analytical result must be a JSON object")
            if transition_run(session, run_id, "SUCCEEDED", result=validated):
                session.commit()
            else:
                session.rollback()
        except Exception as exc:
            session.rollback()
            if transition_run(session, run_id, "FAILED", error=str(exc), expected_status="RUNNING"):
                session.commit()
            else:
                session.rollback()


if __name__ == "__main__":
    execute_run(sys.argv[1])
