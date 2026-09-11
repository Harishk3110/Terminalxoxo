"""Read-only history does not need an ORM identity for every daily bar."""

from datetime import UTC, datetime
from decimal import Decimal

from app import models
from app.price_sources import MarketPriceResolver
from sqlalchemy import event
from sqlalchemy.orm import Session


def test_legacy_projection_preserves_values_without_orm_hydration(ledger_session: Session) -> None:
    session = ledger_session
    stamp = datetime(2025, 12, 31, 20, tzinfo=UTC)
    session.add(
        models.PriceBar(
            id="projected-history",
            instrument_id="AAA",
            timestamp=stamp,
            created_at=stamp,
            interval="1d",
            open=Decimal("101.12345678"),
            high=Decimal("103.23456789"),
            low=Decimal("100.00000001"),
            close=Decimal("102.34567891"),
            volume=None,
            currency="SGD",
            provider="Projection fixture",
            quality="DEMO DATA",
        )
    )
    session.flush()
    session.expunge_all()
    hydrated: list[str] = []

    def observe(target: models.PriceBar, _context: object) -> None:
        hydrated.append(target.id)

    event.listen(models.PriceBar, "load", observe)
    try:
        book = MarketPriceResolver(session, ["AAA"])
    finally:
        event.remove(models.PriceBar, "load", observe)
    selected = book.resolve("AAA", stamp)
    assert selected is not None
    assert selected.value == Decimal("102.34567891")
    assert selected.timestamp == stamp
    assert selected.ingested_at == stamp
    assert selected.id == "projected-history"
    assert selected.source == "Projection fixture"
    assert selected.category == "DEMO"
    assert selected.state == "DEMO"
    assert selected.currency == "SGD"
    assert selected.fields == {
        "open": "101.12345678",
        "high": "103.23456789",
        "low": "100.00000001",
        "close": "102.34567891",
        "volume": None,
    }
    assert hydrated == []
