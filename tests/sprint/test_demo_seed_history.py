"""Fresh history stays deterministic without per-row existence round trips."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from app import models, object_storage
from app.config import Settings
from app.object_storage import ObjectStorage
from app.services import DemoIngestionService
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session


def test_fresh_daily_history_is_complete_exact_and_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Settings.model_validate(
        {
            "object_storage_local_dir": str(tmp_path / "objects"),
            "object_storage_endpoint": None,
            "object_storage_access_key": None,
            "object_storage_secret_key": None,
        }
    )
    monkeypatch.setattr(object_storage, "get_settings", lambda: settings)
    engine = create_engine("sqlite:///" + (tmp_path / "seed.db").as_posix())
    models.Base.metadata.create_all(engine)
    daily_existence_queries = 0

    def observed(
        _connection: object,
        _cursor: object,
        statement: str,
        parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        nonlocal daily_existence_queries
        if (
            "FROM price_bars" in statement
            and "price_bars.timestamp =" in statement
            and isinstance(parameters, tuple)
            and "1d" in parameters
        ):
            daily_existence_queries += 1

    event.listen(engine, "before_cursor_execute", observed)
    try:
        with Session(engine, autoflush=False, expire_on_commit=False) as session:
            service = DemoIngestionService(session, ObjectStorage())
            first = service.seed()
            assert daily_existence_queries == 0
            event.remove(engine, "before_cursor_execute", observed)
            instruments = session.scalar(select(func.count(models.Instrument.id)))
            assert instruments is not None and instruments >= 20
            start, end = date(2016, 9, 5), date(2026, 9, 4)
            days = sum(
                (start + timedelta(days=day)).weekday() < 5 for day in range((end - start).days + 1)
            )
            assert (
                session.scalar(
                    select(func.count(models.PriceBar.id)).where(models.PriceBar.interval == "1d")
                )
                == instruments * days
            )
            bar = session.scalar(
                select(models.PriceBar)
                .join(models.Instrument)
                .where(
                    models.Instrument.symbol == "AAPL",
                    models.PriceBar.interval == "1d",
                    models.PriceBar.timestamp == datetime(2016, 9, 5, tzinfo=UTC),
                )
            )
            assert bar is not None
            assert bar.close == Decimal("39.4") and bar.volume == Decimal("1000000")
            assert bar.currency == "USD" and bar.quality == "DEMO DATA"
            assert bar.raw_object_id is not None
            duplicate = (
                select(
                    models.PriceBar.instrument_id,
                    models.PriceBar.timestamp,
                    models.PriceBar.interval,
                    models.PriceBar.provider,
                )
                .group_by(
                    models.PriceBar.instrument_id,
                    models.PriceBar.timestamp,
                    models.PriceBar.interval,
                    models.PriceBar.provider,
                )
                .having(func.count() > 1)
            )
            assert session.execute(duplicate).first() is None
            event.listen(engine, "before_cursor_execute", observed)
            assert service.seed() == first
            assert daily_existence_queries == 0
    finally:
        engine.dispose()
