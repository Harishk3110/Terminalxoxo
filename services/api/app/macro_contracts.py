"""Serialized macro data keeps observation dates separate from ingestion times."""

from typing import Literal, TypedDict

MAX_OBSERVATIONS = 10_000


class MacroSeriesPayload(TypedDict):
    series_id: str
    title: str
    units: str
    frequency: str
    provider: str
    quality: str


class MacroSeriesList(TypedDict):
    items: list[MacroSeriesPayload]


class MacroDashboardItem(TypedDict):
    series_id: str
    title: str
    latest_value: str | None
    latest_observation_date: str | None
    previous_value: str | None
    change: str | None
    unit: str
    frequency: str
    source: str
    quality: str
    ingestion_timestamp: str | None
    revision_state: Literal["CURRENT", "UNAVAILABLE"]


class MacroDashboardPayload(TypedDict):
    items: list[MacroDashboardItem]


class MacroObservationPayload(TypedDict):
    date: str
    value: str | None
    provider: str
    quality: str
    realtime_start: str | None
    realtime_end: str | None


class MacroHistoryPayload(TypedDict):
    series: MacroSeriesPayload
    observations: list[MacroObservationPayload]
