"""Approved model execution; artifacts are written, never loaded from user input."""

from collections.abc import Mapping
from typing import Literal

import pandas as pd
from pydantic import BaseModel, Field, JsonValue, TypeAdapter
from sqlalchemy.orm import Session

from .model_lab import ModelSettings, model_research
from .model_results import ModelRunResult, PartitionBacktest
from .object_storage import ObjectStorage
from .quant_data import dataset_rows
from .research_inputs import bars_frame


class ModelRunInput(BaseModel):
    dataset_version_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    start: str | None = None
    end: str | None = None
    settings: ModelSettings = Field(default_factory=ModelSettings)


def model_result(session: Session, params: Mapping[str, JsonValue], run_id: str) -> ModelRunResult:
    inputs = ModelRunInput.model_validate(params)
    rows, provenance = dataset_rows(session, inputs.dataset_version_id)
    frame = bars_frame(rows, inputs.symbol, inputs.start, inputs.end)
    settings = inputs.settings
    currency: str | None = (
        TypeAdapter(str | None).validate_python(
            provenance["schema"].get("currency", "DATASET NATIVE"), strict=True
        )
        if settings.model != "KMEANS"
        else None
    )
    result, artifact = model_research(frame, settings)
    backtests: list[PartitionBacktest] = []
    if settings.model != "KMEANS":
        from .backtest_engine import BacktestSettings, simulate

        partitions: tuple[Literal["VALIDATION"], Literal["TEST"]] = ("VALIDATION", "TEST")
        for partition in partitions:
            predictions = [row for row in result["predictions"] if row["partition"] == partition]
            if not predictions:
                continue
            start, end = pd.Timestamp(predictions[0]["date"]), pd.Timestamp(predictions[-1]["date"])
            subset = frame.loc[:end]
            signals = pd.DataFrame({inputs.symbol: float("nan")}, index=subset.index)
            for row in predictions:
                signals.loc[pd.Timestamp(row["date"]), inputs.symbol] = (
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
                {inputs.symbol: subset}, costs, external_signals=signals, evaluation_start=start
            )
            backtests.append(
                {
                    "partition": partition,
                    "currency": currency,
                    "signal_policy": "Positive predicted return or probability above 0.5; long-only next-open daily targets",
                    **analysis,
                }
            )
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
        "cost_backtests": backtests,
        "inputs": provenance,
        "source": provenance["source"],
        "quality": provenance["quality"],
        "as_of": pd.Timestamp(frame.index[-1]).isoformat(),
        "artifact": {
            "object_key": stored.object_key,
            "content_hash": stored.content_hash,
            "size_bytes": stored.size_bytes,
            "format": "joblib / trusted server-generated model",
        },
    }
