"""Approved model execution; artifacts are written, never loaded from user input."""

import pandas as pd

from .model_lab import ModelSettings, model_research
from .object_storage import ObjectStorage
from .quant_data import dataset_rows
from .research_inputs import bars_frame


def model_result(session, params, run_id):
    rows, provenance = dataset_rows(session, params["dataset_version_id"])
    frame = bars_frame(rows, params["symbol"], params.get("start"), params.get("end"))
    settings = ModelSettings(**params.get("settings", {}))
    result, artifact = model_research(frame, settings)
    backtests = []
    if settings.model != "KMEANS":
        from .backtest_engine import BacktestSettings, simulate

        for partition in ("VALIDATION", "TEST"):
            predictions = [row for row in result["predictions"] if row["partition"] == partition]
            if not predictions:
                continue
            start, end = pd.Timestamp(predictions[0]["date"]), pd.Timestamp(predictions[-1]["date"])
            subset = frame.loc[:end]
            signals = pd.DataFrame({params["symbol"]: float("nan")}, index=subset.index)
            for row in predictions:
                signals.loc[pd.Timestamp(row["date"]), params["symbol"]] = (
                    row["probability"] - 0.5
                    if row["probability"] is not None
                    else row["prediction"]
                )
            costs = BacktestSettings(
                fast=5,
                slow=21,
                frequency="DAILY",
                fee_bps=settings.fee_bps,
                slippage_bps=settings.slippage_bps,
            )
            analysis = simulate(
                {params["symbol"]: subset}, costs, external_signals=signals, evaluation_start=start
            )
            backtests.append(
                {
                    "partition": partition,
                    "currency": provenance["schema"].get("currency", "DATASET NATIVE"),
                    "signal_policy": "Positive predicted return or probability above 0.5; long-only next-open daily targets",
                    **analysis,
                }
            )
    result["cost_backtests"] = backtests
    result["warnings"].append(
        "Held-out trading diagnostics separately simulate daily positive-signal targets in the dataset's native currency with recorded fee/slippage assumptions. They are not SGD portfolio returns or paper performance. K-means clusters have no inferred trading direction."
    )
    stored = ObjectStorage().put_bytes(
        key=f"research-models/{run_id}/model.joblib",
        data=artifact,
        content_type="application/octet-stream",
    )
    return {
        **result,
        "inputs": provenance,
        "source": provenance["source"],
        "quality": provenance["quality"],
        "as_of": frame.index[-1].isoformat(),
        "artifact": {
            "object_key": stored.object_key,
            "content_hash": stored.content_hash,
            "size_bytes": stored.size_bytes,
            "format": "joblib / trusted server-generated model",
        },
    }
