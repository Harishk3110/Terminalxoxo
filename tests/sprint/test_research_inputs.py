from collections.abc import Mapping
from pathlib import Path

import pytest
from app import models
from app.model_runs import model_result
from app.object_storage import ObjectStorage
from app.quant_data import dataset_rows
from app.research_inputs import ResearchInput, bars_frame, pin_input
from pydantic import JsonValue, TypeAdapter
from sqlalchemy.orm import Session


def seed_bars(session: Session) -> None:
    import numpy as np
    import pandas as pd

    prices = 100 * np.exp(np.cumsum(np.random.default_rng(3110).normal(0, 0.01, 360)))
    for day, price in zip(pd.bdate_range("2024-01-01", periods=360), prices, strict=True):
        session.add(
            models.PriceBar(
                instrument_id="SPY",
                timestamp=day.to_pydatetime(),
                interval="1d",
                open=price * 0.999,
                high=price * 1.02,
                low=price * 0.98,
                close=price,
                currency="USD",
                provider="DemoProvider",
                quality="DEMO DATA",
            )
        )
    session.flush()


def test_research_snapshot_is_deduplicated_and_hash_verified(
    ledger_session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "object_storage_local_dir", str(tmp_path))
    seed_bars(ledger_session)
    request = ResearchInput(source_mode="DEMO_RESEARCH")
    first = pin_input(ledger_session, request)
    second = pin_input(ledger_session, request)
    assert first == second and first["quality"] == "DEMO DATA"
    assert len(dataset_rows(ledger_session, first["dataset_version_id"])[0]) == 360
    result = model_result(
        ledger_session,
        {"dataset_version_id": first["dataset_version_id"], "symbol": "SPY"},
        "test-model",
    )
    assert (
        result["artifact"]["content_hash"]
        and result["inputs"]["content_hash"] == first["content_hash"]
    )
    assert result["metrics"][2]["partition"] == "TEST"
    key = first["schema"]["curated_key"]
    assert isinstance(key, str)
    ObjectStorage().put_bytes(key=key, data=b"[]", content_type="application/json")
    with pytest.raises(ValueError, match="integrity"):
        dataset_rows(ledger_session, first["dataset_version_id"])


def test_source_aware_missing_open_is_not_synthesised(ledger_session: Session) -> None:
    with pytest.raises(ValueError, match="OHLC"):
        pin_input(ledger_session, ResearchInput(symbol="AAA"))


def test_bar_validation_rejects_duplicates_missing_bounds_and_bad_dates() -> None:
    row = {"date": "2026-01-01", "open": 100, "high": 101, "low": 99, "close": 100}
    for rows in (
        [row, row],
        [{**row, "high": 90}],
        [{**row, "open": None}],
        [{**row, "date": "bad"}],
    ):
        with pytest.raises(ValueError):
            bars_frame(rows, "SPY")


def test_research_date_bounds_are_inclusive_and_preserve_missing_volume() -> None:
    import pandas as pd

    rows: list[Mapping[str, object]] = [
        {
            "date": f"2026-01-0{day}",
            "open": 100,
            "high": 101,
            "low": 99,
            "close": 100,
            "volume": None,
        }
        for day in (5, 6, 7, 8)
    ]
    frame = bars_frame(rows, "SPY", "2026-01-06", "2026-01-07")
    assert pd.DatetimeIndex(frame.index).strftime("%Y-%m-%d").tolist() == [
        "2026-01-06",
        "2026-01-07",
    ]
    assert frame.volume.isna().all()
    with pytest.raises(ValueError, match="empty"):
        bars_frame(rows, "SPY", "2026-01-08", "2026-01-07")


def test_fx_snapshot_uses_only_prior_fixings(
    ledger_session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from datetime import date, timedelta

    from app.backtest_inputs import pin_backtest_inputs
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "object_storage_local_dir", str(tmp_path))
    seed_bars(ledger_session)
    for offset in range(550):
        day = date(2023, 12, 30) + timedelta(days=offset)
        ledger_session.add(
            models.FxRate(
                base_currency="USD",
                quote_currency="SGD",
                date=day,
                rate=1.3 + offset / 10000,
                provider="DemoProvider",
                quality="DEMO DATA",
            )
        )
    ledger_session.flush()
    pinned = pin_backtest_inputs(
        ledger_session, {"symbol": "SPY", "source_mode": "DEMO_RESEARCH", "base_currency": "SGD"}
    )
    objects = TypeAdapter(dict[str, JsonValue])
    fixings = objects.validate_python(pinned["_fx"], strict=True)
    for day_key, raw in objects.validate_python(fixings["SPY"], strict=True).items():
        fixing = objects.validate_python(raw, strict=True)
        provenance = objects.validate_python(fixing["provenance"], strict=True)
        observed, rate = provenance["as_of"], fixing["rate"]
        assert isinstance(observed, str) and isinstance(rate, str)
        assert observed < day_key
        assert float(rate) > 0
    datasets = objects.validate_python(pinned["_datasets"], strict=True)
    assert objects.validate_python(datasets["SPY"], strict=True)["content_hash"]
