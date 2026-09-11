"""FX selection is dated before applying source priority and quote direction."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from app import models
from app.price_sources import FxRateResolver
from sqlalchemy.orm import Session

AT = datetime(2026, 1, 8, 20, tzinfo=UTC)


def observation(
    session: Session,
    *,
    day: int,
    rate: str,
    inverse: bool = False,
    category: str = "PROVIDER",
    source: str = "Dated fixture",
) -> models.FxObservation:
    row = models.FxObservation(
        base_currency="SGD" if inverse else "EUR",
        quote_currency="EUR" if inverse else "SGD",
        timestamp=datetime(2026, 1, day, 20, tzinfo=UTC),
        rate=Decimal(rate),
        source=source,
        source_category=category,
        data_state="DEMO" if category == "DEMO" else "EOD",
    )
    session.add(row)
    session.flush()
    return row


def test_future_direct_does_not_hide_dated_inverse(ledger_session: Session) -> None:
    historical = observation(ledger_session, day=7, rate="0.8", inverse=True)
    observation(ledger_session, day=9, rate="9")
    value, provenance = FxRateResolver(ledger_session).resolve("EUR", "SGD", AT)
    assert value == Decimal("1.25")
    assert provenance["observation_id"] == historical.id
    assert provenance["inverse"] is True and provenance["stale"] is False
    assert provenance["as_of"] == "2026-01-07T20:00:00+00:00"


def test_future_only_observations_never_value_a_historical_book(ledger_session: Session) -> None:
    observation(ledger_session, day=9, rate="1.25")
    observation(ledger_session, day=10, rate="0.8", inverse=True)
    value, provenance = FxRateResolver(ledger_session).resolve("EUR", "SGD", AT)
    assert value is None and provenance["data_state"] == "UNAVAILABLE"
    assert provenance["as_of"] is None


def test_source_priority_applies_across_direct_and_inverse_pairs(ledger_session: Session) -> None:
    observation(ledger_session, day=8, rate="8", category="DEMO", source="Demo fixture")
    provider = observation(ledger_session, day=7, rate="0.8", inverse=True)
    value, provenance = FxRateResolver(ledger_session).resolve("EUR", "SGD", AT)
    assert value == Decimal("1.25") and provenance["observation_id"] == provider.id
    assert provenance["source_category"] == "PROVIDER"


def test_stale_selected_provider_does_not_fall_back_to_fresh_demo(ledger_session: Session) -> None:
    provider = observation(ledger_session, day=1, rate="0.8", inverse=True)
    observation(ledger_session, day=8, rate="9", category="DEMO", source="Demo fixture")
    value, provenance = FxRateResolver(ledger_session).resolve("EUR", "SGD", AT)
    assert value == Decimal("1.25") and provenance["observation_id"] == provider.id
    assert provenance["stale"] is True and provenance["data_state"] == "STALE"


def test_newest_eligible_observation_wins_within_source_priority(ledger_session: Session) -> None:
    observation(ledger_session, day=6, rate="1.2")
    newest = observation(ledger_session, day=8, rate="0.8", inverse=True)
    value, provenance = FxRateResolver(ledger_session).resolve("EUR", "SGD", AT)
    assert value == Decimal("1.25") and provenance["observation_id"] == newest.id


def test_future_observation_does_not_erase_legacy_historical_fx(ledger_session: Session) -> None:
    legacy = models.FxRate(
        base_currency="EUR",
        quote_currency="SGD",
        date=date(2026, 1, 7),
        rate=Decimal("1.25"),
        provider="Legacy provider",
        quality="EOD",
    )
    ledger_session.add(legacy)
    ledger_session.flush()
    observation(ledger_session, day=9, rate="9")
    value, provenance = FxRateResolver(ledger_session).resolve("EUR", "SGD", AT)
    assert value == Decimal("1.25") and provenance["observation_id"] == legacy.id
    assert provenance["source"] == "Legacy provider"


@pytest.mark.parametrize("inverse", [False, True])
@pytest.mark.parametrize("invalid", ["0", "-0.5"])
def test_invalid_selected_rates_are_unavailable_not_demo_fallback(
    ledger_session: Session,
    inverse: bool,
    invalid: str,
) -> None:
    selected = observation(ledger_session, day=8, rate=invalid, inverse=inverse)
    observation(ledger_session, day=8, rate="1.25", category="DEMO", source="Demo fixture")
    value, provenance = FxRateResolver(ledger_session).resolve("EUR", "SGD", AT)
    assert value is None and provenance["data_state"] == "INVALID"
    assert provenance["observation_id"] == selected.id
    assert provenance["source_category"] == "PROVIDER"


def test_identity_conversion_does_not_depend_on_market_observations(
    ledger_session: Session,
) -> None:
    value, provenance = FxRateResolver(ledger_session).resolve("SGD", "SGD", AT)
    assert value == 1 and provenance["source"] == "IDENTITY"
    assert provenance["data_state"] == "CALCULATED" and provenance["stale"] is False
