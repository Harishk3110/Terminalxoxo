"""Immutable, content-addressed OHLC inputs for offline research workers."""

import hashlib
import json
from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from . import models
from .object_storage import ObjectStorage
from .quant_data import dataset_rows
from .terminal_analytics import history, instrument


class ResearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(default="SPY", min_length=1, max_length=40)
    source_mode: Literal["SOURCE_AWARE", "DEMO_RESEARCH"] = "SOURCE_AWARE"
    dataset_version_id: str | None = None
    start: str | None = None
    end: str | None = None


def bars_frame(rows: list[dict], symbol: str, start=None, end=None) -> pd.DataFrame:
    selected = [row for row in rows if row.get("symbol", symbol) == symbol]
    if not selected or len(selected) > 10000:
        raise ValueError("Research requires 1 to 10,000 bars per security")
    frame = pd.DataFrame(selected)
    if not {"date", "open", "high", "low", "close"} <= set(frame):
        raise ValueError(
            "Complete OHLC bars are required; missing opens are not replaced by closes"
        )
    frame.index = pd.DatetimeIndex(
        pd.to_datetime(frame.pop("date"), errors="raise", utc=True)
    ).tz_convert(None)
    if frame.index.hasnans or not frame.index.is_unique or not frame.index.is_monotonic_increasing:
        raise ValueError("Bar dates must be valid, unique and chronological")
    if (frame.index != frame.index.normalize()).any():
        raise ValueError("Only daily research bars are currently supported")
    if "as_of" in frame and any(
        pd.Timestamp(value).date() != day.date()
        for day, value in zip(frame.index, frame.as_of, strict=True)
    ):
        raise ValueError("Carried-forward observations are not executable daily bars")
    for name in ("open", "high", "low", "close"):
        frame[name] = pd.to_numeric(frame[name], errors="raise")
    prices = frame[["open", "high", "low", "close"]]
    if not np.isfinite(prices).all().all() or (prices <= 0).any().any():
        raise ValueError("OHLC bars must be finite and positive")
    if ((frame.high < prices.max(axis=1)) | (frame.low > prices.min(axis=1))).any():
        raise ValueError("OHLC high/low bounds are inconsistent")
    if start:
        frame = frame.loc[pd.Timestamp(start) :]
    if end:
        frame = frame.loc[: pd.Timestamp(end)]
    if frame.empty:
        raise ValueError("Selected research interval is empty")
    return frame


def pin_input(session, request: ResearchInput) -> dict:
    if request.dataset_version_id:
        rows, evidence = dataset_rows(session, request.dataset_version_id)
        bars_frame(rows, request.symbol, request.start, request.end)
        return evidence
    item = instrument(session, request.symbol)
    if request.source_mode == "DEMO_RESEARCH":
        bars = session.scalars(
            select(models.PriceBar)
            .where(
                models.PriceBar.instrument_id == item.id,
                models.PriceBar.interval == "1d",
                models.PriceBar.provider == "DemoProvider",
            )
            .order_by(models.PriceBar.timestamp)
        ).all()
        rows = [
            {
                "date": bar.timestamp.date().isoformat(),
                **{key: float(getattr(bar, key)) for key in ("open", "high", "low", "close")},
                "volume": float(bar.volume) if bar.volume is not None else None,
            }
            for bar in bars
        ]
        source, quality = "DemoProvider independent research fixture", "DEMO DATA"
    else:
        payload = history(session, item.id, 10000)
        rows, source, quality = payload["items"], payload["source"], payload["quality"]
    rows = [{**row, "symbol": item.symbol, "currency": item.currency} for row in rows]
    frame = bars_frame(rows, request.symbol, request.start, request.end)
    selected = set(frame.index.strftime("%Y-%m-%d"))
    rows = [row for row in rows if row["date"] in selected]
    content = json.dumps(rows, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    digest = hashlib.sha256(content).hexdigest()
    key = f"research-inputs/{digest}.json"
    existing = session.scalar(select(models.RawObject).where(models.RawObject.object_key == key))
    if existing:
        version = session.scalar(
            select(models.DatasetVersion).where(models.DatasetVersion.raw_object_id == existing.id)
        )
        if version:
            return dataset_rows(session, version.id)[1]
    storage = ObjectStorage()
    storage.put_bytes(key=key, data=content, content_type="application/json")
    raw = existing or models.RawObject(
        provider=source,
        dataset="research-ohlc",
        object_key=key,
        content_hash=digest,
        content_type="application/json",
        size_bytes=len(content),
        correlation_id=digest,
    )
    session.add(raw)
    dataset = models.Dataset(
        name=f"{item.symbol} / {request.source_mode} / {digest[:12]}",
        dataset_type="ohlcv",
        source=source,
        quality=quality,
    )
    session.add(dataset)
    session.flush()
    version = models.DatasetVersion(
        dataset_id=dataset.id,
        version=1,
        raw_object_id=raw.id,
        row_count=len(rows),
        content_hash=digest,
        schema_json={
            "curated_key": key,
            "curated_hash": digest,
            "source": source,
            "source_mode": request.source_mode,
            "currency": item.currency,
            "symbol": item.symbol,
            "interval": "1d",
            "corporate_actions": "UNADJUSTED / NOT MODELLED",
        },
    )
    session.add(version)
    session.flush()
    session.add(
        models.DatasetLineage(
            dataset_version_id=version.id,
            source_type="PRICE_SNAPSHOT",
            source_id=item.id,
            transform="Immutable OHLC research snapshot; no missing-price fill or adjusted-history inference",
        )
    )
    return dataset_rows(session, version.id)[1]
