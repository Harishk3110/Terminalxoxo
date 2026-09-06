"""Historical cache identity depends on sources, not the current wall-clock minute."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from app import models, portfolio_valuation
from app.portfolio_valuation import PortfolioValuationService
from sqlalchemy import select
from sqlalchemy.orm import Session


class Clock(datetime):
    instant = datetime(2026, 1, 20, 12, 59, 59, tzinfo=UTC)

    @classmethod
    def now(cls, tz=None):
        return cls.instant.astimezone(tz) if tz else cls.instant.replace(tzinfo=None)


def test_historical_run_is_reused_across_wall_clock_minute_and_day_changes(
    ledger_session: Session,
    monkeypatch,
) -> None:
    monkeypatch.setattr(portfolio_valuation, "datetime", Clock)
    monkeypatch.setattr(Clock, "instant", datetime(2026, 1, 20, 12, 59, 59, tzinfo=UTC))
    service = PortfolioValuationService(ledger_session)
    original = service.latest("book", end=date(2026, 1, 7))
    monkeypatch.setattr(Clock, "instant", Clock.instant + timedelta(minutes=1))
    assert service.latest("book", end=date(2026, 1, 7)) == original
    monkeypatch.setattr(Clock, "instant", Clock.instant + timedelta(days=1))
    assert (
        service.latest("book", end=date(2026, 1, 7))["valuation_run_id"]
        == original["valuation_run_id"]
    )


def test_current_day_freshness_still_uses_a_minute_epoch(
    ledger_session: Session, monkeypatch
) -> None:
    monkeypatch.setattr(portfolio_valuation, "datetime", Clock)
    monkeypatch.setattr(Clock, "instant", datetime(2026, 1, 20, 12, 59, 59, tzinfo=UTC))
    service = PortfolioValuationService(ledger_session)
    original = service.fingerprint("book", date(2026, 1, 20))
    assert service.fingerprint("book", date(2026, 1, 20)) == original
    monkeypatch.setattr(Clock, "instant", Clock.instant + timedelta(seconds=1))
    assert service.fingerprint("book", date(2026, 1, 20)) != original


def test_historical_source_changes_and_explicit_force_still_create_new_runs(
    ledger_session: Session,
) -> None:
    service = PortfolioValuationService(ledger_session)
    original = service.latest("book", end=date(2026, 1, 7))
    observation = ledger_session.scalar(select(models.FxObservation).limit(1))
    assert observation is not None
    observation.rate = Decimal("1.31")
    ledger_session.commit()
    changed = service.latest("book", end=date(2026, 1, 7))
    assert changed["valuation_run_id"] != original["valuation_run_id"]
    forced = service.latest("book", end=date(2026, 1, 7), force=True)
    assert forced["valuation_run_id"] not in {
        original["valuation_run_id"],
        changed["valuation_run_id"],
    }
    assert (
        service.latest("book", end=date(2026, 1, 7))["valuation_run_id"]
        == forced["valuation_run_id"]
    )
