"""Historical selection includes both observation stores without future leakage."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from app import models
from app.price_sources import MarketPriceResolver
from sqlalchemy.orm import Session

AT = datetime(2026, 1, 8, 20, tzinfo=UTC)


@pytest.fixture
def market_session(ledger_session: Session) -> Session:
    ledger_session.add(
        models.Instrument(
            id="DATED",
            symbol="DATED",
            name="Dated selection fixture",
            currency="SGD",
            country="Test",
            asset_class="Equity",
            security_type="Common Stock",
        )
    )
    ledger_session.flush()
    return ledger_session


def legacy(
    session: Session, *, day: int = 7, demo: bool = False, interval: str = "1d"
) -> models.PriceBar:
    row = models.PriceBar(
        instrument_id="DATED",
        timestamp=datetime(2026, 1, day, 20, tzinfo=UTC),
        interval=interval,
        open=Decimal("99"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
        volume=None,
        currency="SGD",
        provider="Legacy fixture",
        quality="DEMO DATA" if demo else "EOD",
    )
    session.add(row)
    session.flush()
    return row


def observed(
    session: Session, *, day: int = 9, category: str = "PROVIDER", source: str = "Observed fixture"
) -> models.MarketObservation:
    row = models.MarketObservation(
        instrument_id="DATED",
        timestamp=datetime(2026, 1, day, 20, tzinfo=UTC),
        price=Decimal("120"),
        currency="SGD",
        source=source,
        source_category=category,
        data_state="FILE IMPORT" if category == "FILE" else "EOD",
        fields={},
    )
    session.add(row)
    session.flush()
    return row


def test_future_observation_does_not_hide_legacy_price(market_session: Session) -> None:
    past = legacy(market_session)
    future = observed(market_session)
    resolver = MarketPriceResolver(market_session, ["DATED"])
    chosen = resolver.resolve("DATED", AT)
    assert chosen is not None and chosen.id == past.id and chosen.value == Decimal("105")
    assert future.id not in {row.id for row in resolver.candidates("DATED", AT)}
    assert resolver.describe("DATED", AT)["as_of"] == "2026-01-07T20:00:00+00:00"


def test_history_retains_legacy_and_observation_dates(market_session: Session) -> None:
    past = legacy(market_session)
    current = observed(market_session, day=8)
    rows = MarketPriceResolver(market_session, ["DATED"]).history(
        "DATED", date(2026, 1, 7), date(2026, 1, 8)
    )
    assert [row["date"] for row in rows] == ["2026-01-07", "2026-01-08"]
    assert [row["close"] for row in rows] == [105, 120]
    assert [row["observation_id"] for row in rows] == [past.id, current.id]
    assert rows[0]["volume"] is None


@pytest.mark.parametrize("preferred", ["Observed fixture", "Missing preferred fixture"])
def test_explicit_unavailable_source_does_not_fall_back(
    market_session: Session, preferred: str
) -> None:
    legacy(market_session)
    observed(market_session)
    market_session.add(
        models.SourcePrecedenceRule(
            instrument_id="DATED",
            preferred_source=preferred,
            priority=["BROKER", "PROVIDER", "FILE", "DEMO"],
            stale_after_hours=72,
            reason="Fixture explicitly pins an unavailable historical source",
        )
    )
    market_session.flush()
    resolver = MarketPriceResolver(market_session, ["DATED"])
    assert resolver.resolve("DATED", AT) is None
    assert resolver.describe("DATED", AT)["data_state"] == "UNAVAILABLE"
    assert resolver.history("DATED", date(2026, 1, 7), AT.date()) == []


def test_stale_file_is_not_replaced_by_newer_legacy_demo(market_session: Session) -> None:
    legacy(market_session, day=8, demo=True)
    selected = observed(market_session, day=1, category="FILE")
    provenance = MarketPriceResolver(market_session, ["DATED"]).describe("DATED", AT)
    assert provenance["observation_id"] == selected.id
    assert provenance["data_state"] == "STALE" and provenance["stale"] is True
    assert provenance["as_of"] == "2026-01-01T20:00:00+00:00"


def test_custom_priority_applies_across_both_stores(market_session: Session) -> None:
    legacy(market_session, day=8)
    selected = observed(market_session, day=7, category="FILE")
    market_session.add(
        models.SourcePrecedenceRule(
            instrument_id="DATED",
            priority=["FILE", "PROVIDER", "BROKER", "DEMO"],
            reason="Approved source ordering fixture",
        )
    )
    market_session.flush()
    chosen = MarketPriceResolver(market_session, ["DATED"]).resolve("DATED", AT)
    assert chosen is not None and chosen.id == selected.id


def test_legacy_provider_precedes_newer_demo_observation(market_session: Session) -> None:
    selected = legacy(market_session)
    observed(market_session, day=8, category="DEMO")
    chosen = MarketPriceResolver(market_session, ["DATED"]).resolve("DATED", AT)
    assert chosen is not None and chosen.id == selected.id


def test_daily_selection_excludes_intraday_and_future_legacy_prices(
    market_session: Session,
) -> None:
    legacy(market_session, interval="1m")
    legacy(market_session, day=9)
    observed(market_session)
    resolver = MarketPriceResolver(market_session, ["DATED"])
    assert resolver.resolve("DATED", AT) is None
    assert resolver.history("DATED", date(2026, 1, 7), AT.date()) == []
