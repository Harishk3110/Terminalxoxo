"""Source-aware prices and FX. A stale selected source never falls back to demo."""

from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from collections.abc import Collection
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import NotRequired, TypedDict

from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .portfolio_domain.money import decimal

PRIORITY = ["BROKER", "PROVIDER", "FILE", "DEMO"]


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def close_of_day(day: date) -> datetime:
    return datetime.combine(day, time.max, UTC)


class PriceProvenance(TypedDict):
    source: str
    data_state: str
    stale: bool
    as_of: str | None
    source_category: NotRequired[str]
    source_file_id: NotRequired[str | None]
    dataset_version_id: NotRequired[str | None]
    observation_id: NotRequired[str]
    ingested_at: NotRequired[str]
    currency: NotRequired[str]
    adjustment_state: NotRequired[str]
    original_data_state: NotRequired[str]
    age_hours: NotRequired[float]
    value: NotRequired[str]
    source_file: NotRequired[str | None]
    alternatives: NotRequired[list[PriceAlternative]]
    conflict: NotRequired[bool]
    inverse: NotRequired[bool]
    pair: NotRequired[str]


class PriceAlternative(PriceProvenance):
    difference_pct: float | None


class HistoricalPrice(PriceProvenance):
    date: str
    close: float
    open: float | None
    high: float | None
    low: float | None
    volume: float | None


def _numeric_field(value: JsonValue) -> float | None:
    return float(decimal(value, "OHLCV field")) if value not in (None, "") else None


@dataclass
class Observation:
    value: Decimal
    timestamp: datetime
    ingested_at: datetime
    source: str
    category: str
    state: str
    currency: str
    id: str
    file_id: str | None = None
    version_id: str | None = None
    adjustment: str = "UNADJUSTED"
    fields: dict[str, JsonValue] | None = None

    def provenance(self, at: datetime, tolerance: float = 72) -> PriceProvenance:
        age = max(0, (utc(at) - utc(self.timestamp)).total_seconds() / 3600)
        stale = age > tolerance
        filename = (self.fields or {}).get("filename")
        return {
            "source": self.source,
            "source_category": self.category,
            "source_file_id": self.file_id,
            "dataset_version_id": self.version_id,
            "observation_id": self.id,
            "as_of": utc(self.timestamp).isoformat(),
            "ingested_at": utc(self.ingested_at).isoformat(),
            "currency": self.currency,
            "adjustment_state": self.adjustment,
            "data_state": "STALE"
            if stale
            else "DEMO DATA"
            if self.category == "DEMO"
            else self.state,
            "original_data_state": self.state,
            "age_hours": round(age, 2),
            "stale": stale,
            "value": str(self.value),
            "source_file": filename if isinstance(filename, str) else None,
        }


type ObservationGroups = dict[tuple[str, str], tuple[list[datetime], list[Observation]]]


class MarketPriceResolver:
    def __init__(
        self, session: Session, instrument_ids: Collection[str], start: date | None = None
    ) -> None:
        self.instruments = {
            r.id: r
            for r in session.scalars(
                select(models.Instrument).where(models.Instrument.id.in_(instrument_ids))
            ).all()
        }
        self.rules = {
            r.instrument_id: r for r in session.scalars(select(models.SourcePrecedenceRule)).all()
        }
        self.series: dict[str, list[Observation]] = defaultdict(list)
        rows = session.scalars(
            select(models.MarketObservation).where(
                models.MarketObservation.instrument_id.in_(instrument_ids)
            )
        ).all()
        for row in rows:
            self.series[row.instrument_id].append(
                Observation(
                    row.price,
                    utc(row.timestamp),
                    utc(row.created_at),
                    row.source,
                    row.source_category,
                    row.data_state,
                    row.currency,
                    row.id,
                    row.source_file_id,
                    row.dataset_version_id,
                    row.adjustment_state,
                    row.fields,
                )
            )
        missing = [key for key in instrument_ids if key not in self.series]
        if missing:
            query = select(models.PriceBar).where(
                models.PriceBar.instrument_id.in_(missing), models.PriceBar.interval == "1d"
            )
            if start:
                query = query.where(
                    models.PriceBar.timestamp
                    >= datetime.combine(start - timedelta(days=400), time.min)
                )
            for bar in session.scalars(query).all():
                category = "DEMO" if bar.quality == "DEMO DATA" else "PROVIDER"
                self.series[bar.instrument_id].append(
                    Observation(
                        bar.close,
                        utc(bar.timestamp),
                        utc(bar.created_at),
                        bar.provider,
                        category,
                        "DEMO" if category == "DEMO" else "EOD",
                        bar.currency,
                        bar.id,
                        fields={
                            "open": str(bar.open),
                            "high": str(bar.high),
                            "low": str(bar.low),
                            "close": str(bar.close),
                            "volume": str(bar.volume) if bar.volume is not None else None,
                        },
                    )
                )
        self.grouped: dict[str, ObservationGroups] = {}
        for key, values in self.series.items():
            groups: dict[tuple[str, str], list[Observation]] = defaultdict(list)
            for value in values:
                groups[(value.category, value.source)].append(value)
            self.grouped[key] = {}
            for group, observations in groups.items():
                observations.sort(key=lambda x: (x.timestamp, x.ingested_at, x.id))
                self.grouped[key][group] = ([x.timestamp for x in observations], observations)

    def candidates(self, instrument_id: str, at: datetime) -> list[Observation]:
        result = []
        for _, (dates, rows) in self.grouped.get(instrument_id, {}).items():
            index = bisect_right(dates, utc(at)) - 1
            if index >= 0:
                result.append(rows[index])
        return result

    def resolve(self, instrument_id: str, at: datetime) -> Observation | None:
        candidates = self.candidates(instrument_id, at)
        rule = self.rules.get(instrument_id)
        if rule and rule.preferred_source:
            candidates = [r for r in candidates if r.source == rule.preferred_source]
        priority = rule.priority if rule else PRIORITY
        for category in priority:
            matches = [r for r in candidates if r.category == category]
            if matches:
                return max(matches, key=lambda r: (r.timestamp, r.ingested_at, r.id))
        return None

    def describe(self, instrument_id: str, at: datetime) -> PriceProvenance:
        chosen = self.resolve(instrument_id, at)
        rule = self.rules.get(instrument_id)
        if chosen is None:
            return {
                "data_state": "UNAVAILABLE",
                "source": "UNAVAILABLE",
                "stale": False,
                "as_of": None,
            }
        result = chosen.provenance(at, rule.stale_after_hours if rule else 72)
        alternatives: list[PriceAlternative] = []
        for item in self.candidates(instrument_id, at):
            if item.id != chosen.id and item.timestamp.date() == chosen.timestamp.date():
                difference = abs(item.value / chosen.value - 1) if chosen.value else None
                alternatives.append(
                    {
                        **item.provenance(at),
                        "difference_pct": float(difference) if difference is not None else None,
                    }
                )
        result["alternatives"] = alternatives
        result["conflict"] = any((r["difference_pct"] or 0) > 0.01 for r in alternatives)
        return result

    def history(self, instrument_id: str, start: date, end: date) -> list[HistoricalPrice]:
        days = sorted(
            {
                o.timestamp.date()
                for o in self.series.get(instrument_id, [])
                if start <= o.timestamp.date() <= end
            }
        )
        rows: list[HistoricalPrice] = []
        for day in days:
            observation = self.resolve(instrument_id, close_of_day(day))
            if observation:
                fields = observation.fields or {}
                rows.append(
                    {
                        "date": day.isoformat(),
                        "close": float(observation.value),
                        "open": _numeric_field(fields.get("open")),
                        "high": _numeric_field(fields.get("high")),
                        "low": _numeric_field(fields.get("low")),
                        "volume": _numeric_field(fields.get("volume")),
                        **observation.provenance(close_of_day(day)),
                    }
                )
        return rows


class FxRateResolver:
    def __init__(self, session: Session) -> None:
        self.series: dict[tuple[str, str], list[Observation]] = defaultdict(list)
        for row in session.scalars(select(models.FxObservation)).all():
            self.series[(row.base_currency, row.quote_currency)].append(
                Observation(
                    row.rate,
                    utc(row.timestamp),
                    utc(row.created_at),
                    row.source,
                    row.source_category,
                    row.data_state,
                    row.quote_currency,
                    row.id,
                    row.source_file_id,
                )
            )
        existing = set(self.series)
        for rate in session.scalars(select(models.FxRate).order_by(models.FxRate.date)).all():
            key = (rate.base_currency, rate.quote_currency)
            if key not in existing:
                category = "DEMO" if rate.quality == "DEMO DATA" else "PROVIDER"
                self.series[key].append(
                    Observation(
                        rate.rate,
                        datetime.combine(rate.date, time.min, UTC),
                        utc(rate.created_at),
                        rate.provider,
                        category,
                        "DEMO" if category == "DEMO" else "EOD",
                        rate.quote_currency,
                        rate.id,
                    )
                )
        self.groups: dict[tuple[str, str], ObservationGroups] = {}
        for key, rows in self.series.items():
            groups: dict[tuple[str, str], list[Observation]] = defaultdict(list)
            for observation in rows:
                groups[(observation.category, observation.source)].append(observation)
            self.groups[key] = {}
            for group, values in groups.items():
                values.sort(key=lambda r: (r.timestamp, r.ingested_at))
                self.groups[key][group] = ([r.timestamp for r in values], values)

    def resolve(
        self, currency: str, base: str, at: datetime
    ) -> tuple[Decimal | None, PriceProvenance]:
        if currency == base:
            return Decimal("1"), {
                "source": "IDENTITY",
                "data_state": "CALCULATED",
                "as_of": utc(at).isoformat(),
                "stale": False,
                "value": "1",
            }
        reverse = (currency, base) not in self.groups and (base, currency) in self.groups
        groups = self.groups.get((base, currency) if reverse else (currency, base), {})
        candidates = []
        for dates, rows in groups.values():
            index = bisect_right(dates, utc(at)) - 1
            if index >= 0:
                candidates.append(rows[index])
        for category in PRIORITY:
            matches = [r for r in candidates if r.category == category]
            if matches:
                row = max(matches, key=lambda r: (r.timestamp, r.ingested_at))
                value = 1 / row.value if reverse else row.value
                return value, {**row.provenance(at), "value": str(value), "inverse": reverse}
        return None, {
            "source": "UNAVAILABLE",
            "data_state": "UNAVAILABLE",
            "as_of": None,
            "stale": False,
            "pair": f"{currency}/{base}",
        }
