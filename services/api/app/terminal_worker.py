"""Isolated process for approved analytical templates; never evaluates user code."""
from __future__ import annotations

import sys
import json
import hashlib
from datetime import datetime, timezone

import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover
from sqlalchemy import select

from . import models
from .database import SessionLocal
from .object_storage import ObjectStorage
from .services import infer_tabular
from .terminal_analytics import VERSION, history, safe_number, stress_result


class MovingAverageTemplate(Strategy):
    fast = 20
    slow = 50

    def init(self):
        self.fast_line = self.I(lambda x: pd.Series(x).rolling(self.fast).mean(), self.data.Close)
        self.slow_line = self.I(lambda x: pd.Series(x).rolling(self.slow).mean(), self.data.Close)

    def next(self):
        if crossover(self.fast_line, self.slow_line) and not self.position:
            self.buy(size=.95)
        elif crossover(self.slow_line, self.fast_line) and self.position:
            self.position.close()


def backtest_result(session, params):
    dataset_id = params.get("dataset_id")
    if dataset_id:
        version = session.get(models.DatasetVersion, params["dataset_version_id"])
        raw = session.get(models.RawObject, version.raw_object_id)
        schema = version.schema_json or {}
        if schema.get("curated_key"):
            content = ObjectStorage().get_bytes(schema["curated_key"])
            if hashlib.sha256(content).hexdigest() != schema["curated_hash"]:
                raise ValueError("Pinned dataset integrity check failed")
            rows = json.loads(content)
            symbols = {r.get("symbol") for r in rows}
            if len(symbols) > 1:
                rows = [r for r in rows if r.get("symbol") == params.get("symbol")]
            if not rows or any(r.get(k) is None for r in rows for k in ("date", "open", "high", "low", "close")):
                raise ValueError("Pinned dataset requires complete validated OHLC bars")
        else:
            rows, _ = infer_tabular(ObjectStorage().get_bytes(raw.object_key), params.get("suffix", "csv"))
            mapping = params.get("mapping") or {"date": "date", "close": "close"}
            rows = [{role: row.get(column) for role, column in mapping.items()} for row in rows]
        data_source = schema.get("source", "USER_UPLOAD")
        quality = "FILE IMPORT" if schema.get("file_id") else "USER PROVIDED"
    else:
        payload = history(session, params.get("symbol", "SPY"))
        rows, data_source, quality = payload["items"], payload["source"], payload["quality"]
    frame = pd.DataFrame(rows)
    frame.index = pd.to_datetime(frame.pop("date"))
    frame = frame.sort_index()
    frame = frame[~frame.index.duplicated()]
    for column in ("close", "open", "high", "low"):
        frame[column] = pd.to_numeric(frame[column] if column in frame else frame["close"], errors="raise")
    frame = frame.rename(columns={k: k.title() for k in frame.columns})
    if params.get("start"):
        frame = frame.loc[params["start"]:]
    if params.get("end"):
        frame = frame.loc[:params["end"]]
    fast, slow = int(params.get("fast", 20)), int(params.get("slow", 50))
    if not 1 <= fast < slow <= 500 or len(frame) <= slow + 2:
        raise ValueError("Require 1 <= fast < slow <= 500 and enough valid observations")
    capital = float(params.get("capital", 70000))
    fee = float(params.get("fee_bps", 5)) / 10000
    spread = float(params.get("slippage_bps", 5)) / 10000
    if capital < 100 or capital > 1e9 or not 0 <= fee <= .05 or not 0 <= spread <= .05:
        raise ValueError("Capital or cost assumptions exceed bounds")
    engine = Backtest(frame, MovingAverageTemplate, cash=capital, commission=fee, spread=spread, trade_on_close=False, exclusive_orders=True, finalize_trades=True)
    result = engine.run(fast=fast, slow=slow)
    curve = result["_equity_curve"]
    trades = result["_trades"]
    records = [{"date": day.date().isoformat(), "equity": float(row.Equity), "benchmark": capital * float(frame.loc[day, "Close"] / frame.iloc[0].Close), "drawdown": -float(row.DrawdownPct)} for day, row in curve.iterrows()]
    return {"equity_curve": records, "metrics": {"total_return": safe_number(result["Return [%]"] / 100), "cagr": safe_number(result["Return (Ann.) [%]"] / 100), "sharpe": safe_number(result["Sharpe Ratio"]), "max_drawdown": safe_number(result["Max. Drawdown [%]"] / 100), "volatility": safe_number(result["Volatility (Ann.) [%]"] / 100), "trade_count": int(result["# Trades"])}, "initial_capital": capital, "final_equity": float(result["Equity Final [$]"]), "trades": [{"entry": row.EntryTime.isoformat(), "exit": row.ExitTime.isoformat(), "quantity": int(row.Size), "entry_price": float(row.EntryPrice), "exit_price": float(row.ExitPrice), "pnl": float(row.PnL)} for _, row in trades.iterrows()], "source": data_source, "quality": quality, "as_of": frame.index[-1].isoformat(), "parameters": params, "calculation_version": f"backtesting.py 0.6.5 / {VERSION}", "warnings": ["Historical simulation, not a forecast. Signals fill at the next open; fees and spread are included. Long-only moving-average template.", "Survivorship, liquidity, financing, taxes and corporate-action adjustments are not modelled."]}


def execute_run(run_id: str):
    with SessionLocal() as session:
        run = session.get(models.AnalysisRun, run_id)
        if not run or run.status != "QUEUED":
            return
        run.status = "RUNNING"
        run.started_at = datetime.now(timezone.utc)
        run.history = [*run.history, {"state": "RUNNING", "at": run.started_at.isoformat(), "message": "Validated template executing in isolated process"}]
        session.commit()
        try:
            result = stress_result(session, run.parameters) if run.kind == "stress" else backtest_result(session, run.parameters)
            session.refresh(run)
            if run.status == "CANCELLED":
                return
            run.result = result
            run.status = "SUCCEEDED"
        except Exception as exc:
            session.rollback()
            run = session.get(models.AnalysisRun, run_id)
            if run.status == "CANCELLED":
                return
            run.status = "FAILED"
            run.error = str(exc)
        run.finished_at = datetime.now(timezone.utc)
        run.history = [*run.history, {"state": run.status, "at": run.finished_at.isoformat(), "message": run.error or "Result persisted"}]
        session.commit()


if __name__ == "__main__":
    execute_run(sys.argv[1])
