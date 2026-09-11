from datetime import UTC, date, datetime
from decimal import Decimal
from typing import get_args, get_type_hints

import pytest
from app import models
from app.price_sources import MarketPriceResolver
from app.repositories import DatasetRepository, MarketRepository, RepositoryError
from sqlalchemy import Date, func, select


def add_fx(session, base, quote, day, rate):
    session.add(
        models.FxRate(
            base_currency=base,
            quote_currency=quote,
            date=day,
            rate=Decimal(rate),
            provider="FIXTURE",
            quality="TEST",
        )
    )
    session.flush()


def test_inverse_fx_is_bounded_by_requested_date(ledger_session):
    add_fx(ledger_session, "SGD", "USD", date(2026, 1, 1), "0.8")
    add_fx(ledger_session, "SGD", "USD", date(2026, 2, 1), "0.5")
    repo = MarketRepository(ledger_session)
    assert repo.fx_rate("USD", "SGD", date(2026, 1, 15)) == Decimal("1.25")
    assert repo.fx_rate("USD", "SGD") == Decimal("2")


def test_future_inverse_fx_cannot_fill_missing_history(ledger_session):
    add_fx(ledger_session, "SGD", "USD", date(2026, 2, 1), "0.5")
    with pytest.raises(RepositoryError, match="Missing FX"):
        MarketRepository(ledger_session).fx_rate("USD", "SGD", date(2026, 1, 15))


def test_direct_fx_and_identity_preserve_existing_precedence(ledger_session):
    add_fx(ledger_session, "USD", "SGD", date(2026, 1, 1), "1.3")
    add_fx(ledger_session, "USD", "SGD", date(2026, 2, 1), "1.5")
    add_fx(ledger_session, "SGD", "USD", date(2026, 1, 1), "0.8")
    repo = MarketRepository(ledger_session)
    assert repo.fx_rate("USD", "SGD", date(2026, 1, 15)) == Decimal("1.3")
    assert repo.fx_rate("SGD", "SGD", date(2026, 1, 15)) == Decimal("1")


def test_sql_date_annotations_match_materialized_values():
    checked = 0
    for mapper in models.Base.registry.mappers:
        hints = get_type_hints(mapper.class_)
        for column in mapper.columns:
            if not isinstance(column.type, Date):
                continue
            annotation = get_args(hints[column.key])[0]
            assert annotation is date or date in get_args(annotation), (
                mapper.class_.__name__,
                column.key,
                annotation,
            )
            checked += 1
    assert checked >= 25


@pytest.mark.parametrize(
    "columns", [None, {}, ["not a column"], [{}], [{"name": 42, "type": "number"}]]
)
def test_invalid_dataset_schema_fails_before_persistence(ledger_session, columns):
    with pytest.raises(ValueError):
        DatasetRepository(ledger_session).create_dataset_version(
            dataset_name="Fixture",
            dataset_type="prices",
            source="FIXTURE",
            quality="TEST",
            raw_object_id="not-created",
            row_count=1,
            content_hash="0" * 64,
            schema_json={"columns": columns},
        )
    assert ledger_session.scalar(select(func.count()).select_from(models.Dataset)) == 0
    assert not ledger_session.new


@pytest.mark.parametrize("volume", [None, Decimal("0"), Decimal("25")])
def test_price_bar_history_preserves_missing_versus_zero_volume(ledger_session, volume):
    ledger_session.add(
        models.Instrument(
            id="CASH_TEST",
            symbol="CASH_TEST",
            name="Fictional contract test security",
            currency="SGD",
            country="Test",
            asset_class="Equity",
            security_type="Common Stock",
        )
    )
    ledger_session.flush()
    ledger_session.add(
        models.PriceBar(
            instrument_id="CASH_TEST",
            timestamp=datetime(2026, 1, 5, 20, tzinfo=UTC),
            interval="1d",
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("90"),
            close=Decimal("105"),
            volume=volume,
            currency="SGD",
            provider="FIXTURE",
            quality="TEST",
        )
    )
    ledger_session.flush()
    rows = MarketPriceResolver(ledger_session, ["CASH_TEST"]).history(
        "CASH_TEST", date(2026, 1, 5), date(2026, 1, 5)
    )
    assert len(rows) == 1
    assert rows[0]["volume"] == (float(volume) if volume is not None else None)
