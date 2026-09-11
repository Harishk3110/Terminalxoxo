"""Source-aware prices and FX. A stale selected source never falls back to demo."""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from . import models

PRIORITY = ["BROKER", "PROVIDER", "FILE", "DEMO"]


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def close_of_day(day: date):
    return datetime.combine(day, time.max, timezone.utc)


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
    fields: dict | None = None

    def provenance(self, at: datetime, tolerance=72):
        age = max(0, (utc(at) - utc(self.timestamp)).total_seconds() / 3600)
        stale = age > tolerance
        return {
            "source": self.source, "source_category": self.category,
            "source_file_id": self.file_id, "dataset_version_id": self.version_id,
            "observation_id": self.id, "as_of": utc(self.timestamp).isoformat(),
            "ingested_at": utc(self.ingested_at).isoformat(),
            "currency": self.currency, "adjustment_state": self.adjustment,
            "data_state": "STALE" if stale else "DEMO DATA" if self.category == "DEMO" else self.state,
            "original_data_state": self.state, "age_hours": round(age, 2),
            "stale": stale, "value": str(self.value),
            "source_file": (self.fields or {}).get("filename"),
        }


class MarketPriceResolver:
    def __init__(self, session, instrument_ids, start: date | None = None):
        self.instruments = {r.id: r for r in session.scalars(select(models.Instrument).where(models.Instrument.id.in_(instrument_ids))).all()}
        self.rules = {r.instrument_id: r for r in session.scalars(select(models.SourcePrecedenceRule)).all()}
        self.series = defaultdict(list)
        rows = session.scalars(select(models.MarketObservation).where(models.MarketObservation.instrument_id.in_(instrument_ids))).all()
        for row in rows:
            self.series[row.instrument_id].append(Observation(
                row.price, utc(row.timestamp), utc(row.created_at), row.source,
                row.source_category, row.data_state, row.currency, row.id,
                row.source_file_id, row.dataset_version_id, row.adjustment_state, row.fields,
            ))
        missing = [key for key in instrument_ids if key not in self.series]
        if missing:
            query = select(models.PriceBar).where(models.PriceBar.instrument_id.in_(missing), models.PriceBar.interval == "1d")
            if start:
                query = query.where(models.PriceBar.timestamp >= datetime.combine(start - timedelta(days=400), time.min))
            for row in session.scalars(query).all():
                category = "DEMO" if row.quality == "DEMO DATA" else "PROVIDER"
                self.series[row.instrument_id].append(Observation(row.close, utc(row.timestamp), utc(row.created_at), row.provider, category, "DEMO" if category == "DEMO" else "EOD", row.currency, row.id,
                    fields={"open": str(row.open), "high": str(row.high), "low": str(row.low), "close": str(row.close), "volume": str(row.volume or 0)}))
        self.grouped = {}
        for key, values in self.series.items():
            groups = defaultdict(list)
            for value in values:
                groups[(value.category, value.source)].append(value)
            self.grouped[key] = {}
            for group, observations in groups.items():
                observations.sort(key=lambda x: (x.timestamp, x.ingested_at, x.id))
                self.grouped[key][group] = ([x.timestamp for x in observations], observations)

    def candidates(self, instrument_id, at):
        result = []
        for _, (dates, rows) in self.grouped.get(instrument_id, {}).items():
            index = bisect_right(dates, utc(at)) - 1
            if index >= 0:
                result.append(rows[index])
        return result

    def resolve(self, instrument_id, at):
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

    def describe(self, instrument_id, at):
        chosen = self.resolve(instrument_id, at)
        rule = self.rules.get(instrument_id)
        if chosen is None:
            return {"data_state": "UNAVAILABLE", "source": "UNAVAILABLE", "stale": False, "as_of": None}
        result = chosen.provenance(at, rule.stale_after_hours if rule else 72)
        alternatives = []
        for item in self.candidates(instrument_id, at):
            if item.id != chosen.id and item.timestamp.date() == chosen.timestamp.date():
                difference = abs(item.value / chosen.value - 1) if chosen.value else None
                alternatives.append({**item.provenance(at), "difference_pct": float(difference) if difference is not None else None})
        result["alternatives"] = alternatives
        result["conflict"] = any((r["difference_pct"] or 0) > .01 for r in alternatives)
        return result

    def history(self, instrument_id, start, end):
        days = sorted({o.timestamp.date() for o in self.series.get(instrument_id, []) if start <= o.timestamp.date() <= end})
        rows = []
        for day in days:
            observation = self.resolve(instrument_id, close_of_day(day))
            if observation:
                fields = observation.fields or {}
                rows.append({
                    "date": day.isoformat(), "close": float(observation.value),
                    **{k: float(fields[k]) if fields.get(k) not in (None, "") else None for k in ("open", "high", "low", "volume")},
                    **observation.provenance(close_of_day(day)),
                })
        return rows


class FxRateResolver:
    def __init__(self, session):
        self.series = defaultdict(list)
        for row in session.scalars(select(models.FxObservation)).all():
            self.series[(row.base_currency, row.quote_currency)].append(Observation(row.rate, utc(row.timestamp), utc(row.created_at), row.source, row.source_category, row.data_state, row.quote_currency, row.id, row.source_file_id))
        existing = set(self.series)
        for row in session.scalars(select(models.FxRate).order_by(models.FxRate.date)).all():
            key = (row.base_currency, row.quote_currency)
            if key not in existing:
                category = "DEMO" if row.quality == "DEMO DATA" else "PROVIDER"
                self.series[key].append(Observation(row.rate, datetime.combine(row.date, time.min, timezone.utc), utc(row.created_at), row.provider, category, "DEMO" if category == "DEMO" else "EOD", row.quote_currency, row.id))
        self.groups = {}
        for key, rows in self.series.items():
            groups = defaultdict(list)
            for row in rows:
                groups[(row.category, row.source)].append(row)
            self.groups[key] = {}
            for group, values in groups.items():
                values.sort(key=lambda r: (r.timestamp, r.ingested_at))
                self.groups[key][group] = ([r.timestamp for r in values], values)

    def resolve(self, currency, base, at):
        if currency == base:
            return Decimal("1"), {"source": "IDENTITY", "data_state": "CALCULATED", "as_of": utc(at).isoformat(), "stale": False, "value": "1"}
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
        return None, {"source": "UNAVAILABLE", "data_state": "UNAVAILABLE", "as_of": None, "stale": False, "pair": f"{currency}/{base}"}
