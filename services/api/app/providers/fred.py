from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx
from pydantic import BaseModel, Field

from ..config import Settings
from .base import MacroDataProvider, ProviderState, ProviderStatus
from .http import ProviderError, fetch


class FredProviderError(ProviderError):
    pass


class FredSeries(BaseModel):
    id: str
    realtime_start: str | None = None
    realtime_end: str | None = None
    title: str
    observation_start: str | None = None
    observation_end: str | None = None
    frequency: str | None = None
    frequency_short: str | None = None
    units: str | None = None
    units_short: str | None = None
    seasonal_adjustment: str | None = None
    seasonal_adjustment_short: str | None = None
    last_updated: str | None = None
    popularity: int | None = None
    notes: str | None = None


class FredSeriesResponse(BaseModel):
    realtime_start: str | None = None
    realtime_end: str | None = None
    seriess: list[FredSeries] = Field(default_factory=list)


class FredObservation(BaseModel):
    realtime_start: str | None = None
    realtime_end: str | None = None
    date: str
    value: str

    @property
    def decimal_value(self) -> Decimal | None:
        if self.value == ".":
            return None
        return Decimal(self.value)


class FredObservationsResponse(BaseModel):
    realtime_start: str | None = None
    realtime_end: str | None = None
    observation_start: str | None = None
    observation_end: str | None = None
    units: str | None = None
    output_type: int | None = None
    file_type: str | None = None
    order_by: str | None = None
    sort_order: str | None = None
    count: int | None = None
    offset: int | None = None
    limit: int | None = None
    observations: list[FredObservation] = Field(default_factory=list)


class FredVintageDatesResponse(BaseModel):
    realtime_start: str | None = None
    realtime_end: str | None = None
    order_by: str | None = None
    sort_order: str | None = None
    count: int | None = None
    offset: int | None = None
    limit: int | None = None
    vintage_dates: list[str] = Field(default_factory=list)


class FredProvider(MacroDataProvider):
    provider_name = "FRED"
    capabilities = [
        "test_connection",
        "search_series",
        "metadata",
        "observations",
        "vintage_dates",
        "backfill",
        "refresh",
    ]

    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self.settings = settings
        self.transport = transport
        self._last_success: datetime | None = None
        self._last_failure: datetime | None = None
        self._last_error: str | None = None
        self._rate_limit_state: str | None = None

    @property
    def configured(self) -> bool:
        return bool(self.settings.fred_enabled and self.settings.fred_api_key)

    def status(self) -> ProviderStatus:
        state = (
            ProviderState.CONNECTED
            if self._last_success
            else (ProviderState.NOT_CONFIGURED if not self.configured else ProviderState.CONNECTING)
        )
        if self._last_error and self.configured:
            state = ProviderState.FAILED
        return ProviderStatus(
            provider_name=self.provider_name,
            capabilities=self.capabilities,
            connection_state=state,
            configured=self.configured,
            enabled=self.settings.fred_enabled,
            last_success=self._last_success,
            last_failure=self._last_failure,
            last_error=self._last_error,
            data_freshness=None,
            rate_limit_state=self._rate_limit_state,
        )

    async def test_connection(self, correlation_id: str) -> ProviderStatus:
        if not self.configured:
            self._last_error = "FRED_API_KEY is not configured"
            return self.status()
        await self.series_metadata("GDP", correlation_id)
        self._last_success = datetime.now(UTC)
        self._last_error = None
        return self.status()

    async def health_check(self, correlation_id: str) -> ProviderStatus:
        return await self.test_connection(correlation_id) if self.configured else self.status()

    async def search_series(self, query: str, correlation_id: str) -> dict:
        return await self._request(
            "series/search", {"search_text": query, "limit": 25}, correlation_id
        )

    async def series_metadata(self, series_id: str, correlation_id: str) -> dict:
        payload = await self._request("series", {"series_id": series_id}, correlation_id)
        FredSeriesResponse.model_validate(payload)
        return payload

    async def observations(
        self, series_id: str, correlation_id: str, observation_start: str | None = None
    ) -> dict:
        params: dict[str, Any] = {"series_id": series_id, "sort_order": "asc", "limit": 100000}
        if observation_start:
            params["observation_start"] = observation_start
        payload = await self._request("series/observations", params, correlation_id)
        FredObservationsResponse.model_validate(payload)
        return payload

    async def vintage_dates(self, series_id: str, correlation_id: str) -> dict:
        payload = await self._request(
            "series/vintagedates",
            {"series_id": series_id, "sort_order": "asc", "limit": 10000},
            correlation_id,
        )
        FredVintageDatesResponse.model_validate(payload)
        return payload

    async def _request(self, path: str, params: dict[str, Any], correlation_id: str) -> dict:
        if not self.settings.fred_api_key:
            raise FredProviderError("FRED_API_KEY is required")
        request_params = {**params, "api_key": self.settings.fred_api_key, "file_type": "json"}
        headers = {"X-Correlation-ID": correlation_id, "User-Agent": "KnK-Capital-Terminal/0.1"}
        try:
            response = await fetch(
                "FRED",
                self.settings.fred_base_url.rstrip("/") + "/" + path,
                params=request_params,
                headers=headers,
                transport=self.transport,
            )
            if not isinstance(response.payload, dict):
                raise ProviderError("FRED response must be an object")
            self._last_success = datetime.now(UTC)
            self._last_error = None
            self._rate_limit_state = response.rate_remaining
            return {
                **response.payload,
                "_knk_latency_ms": response.latency_ms,
                "_knk_correlation_id": correlation_id,
            }
        except ProviderError as exc:
            self._last_failure = datetime.now(UTC)
            self._last_error = str(exc)
            self._rate_limit_state = exc.state
            raise FredProviderError(str(exc), exc.state, exc.status_code, exc.retry_after) from exc
