from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol


class ProviderState(StrEnum):
    DISABLED = "DISABLED"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    RATE_LIMITED = "RATE_LIMITED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ProviderStatus:
    provider_name: str
    capabilities: list[str]
    connection_state: ProviderState
    configured: bool
    enabled: bool
    last_success: datetime | None
    last_failure: datetime | None
    last_error: str | None
    data_freshness: str | None
    rate_limit_state: str | None


class Provider(Protocol):
    provider_name: str
    capabilities: list[str]

    async def test_connection(self, correlation_id: str) -> ProviderStatus:
        ...

    async def health_check(self, correlation_id: str) -> ProviderStatus:
        ...


class MacroDataProvider(Provider, Protocol):
    async def search_series(self, query: str, correlation_id: str) -> dict:
        ...

    async def series_metadata(self, series_id: str, correlation_id: str) -> dict:
        ...

    async def observations(self, series_id: str, correlation_id: str, observation_start: str | None = None) -> dict:
        ...

    async def vintage_dates(self, series_id: str, correlation_id: str) -> dict:
        ...


class MarketDataProvider(Provider, Protocol):
    pass


class FundamentalDataProvider(Provider, Protocol):
    pass


class InstrumentReferenceProvider(Provider, Protocol):
    pass


class FXDataProvider(Provider, Protocol):
    pass


class FilingProvider(Provider, Protocol):
    pass


class BrokerProvider(Provider, Protocol):
    pass


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        self._providers[provider.provider_name] = provider

    def get(self, provider_name: str) -> Provider | None:
        return self._providers.get(provider_name)

    def list(self) -> list[Provider]:
        return list(self._providers.values())
