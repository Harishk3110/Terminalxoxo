"""Read-only, vendor-neutral JSON market/options adapter contract."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal, Self
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator

from ..config import Settings
from ..option_contracts import ChainContract
from .http import ProviderError, Response, fetch


class PriceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    symbol: str = Field(min_length=1, max_length=40)
    timestamp: datetime
    close: Decimal = Field(gt=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    open: Decimal | None = Field(default=None, gt=0)
    high: Decimal | None = Field(default=None, gt=0)
    low: Decimal | None = Field(default=None, gt=0)
    volume: Decimal | None = Field(default=None, ge=0)
    data_state: Literal["EOD", "DELAYED", "LIVE"]
    adjustment_state: Literal["UNADJUSTED", "ADJUSTED"]

    @model_validator(mode="after")
    def validate_bar(self) -> Self:
        if self.timestamp.tzinfo is None or self.timestamp > datetime.now(UTC):
            raise ValueError("Price timestamp must be timezone-aware and not future")
        values = [self.close] + ([self.open] if self.open is not None else [])
        if self.high is not None and self.high < max(values):
            raise ValueError("High is below open or close")
        if self.low is not None and self.low > min(values):
            raise ValueError("Low is above open or close")
        if self.high is not None and self.low is not None and self.high < self.low:
            raise ValueError("High is below low")
        return self


class JsonMarketProvider:
    def __init__(
        self,
        settings: Settings,
        kind: Literal["market", "options"] = "market",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.kind, self.transport = kind, transport
        self.provider_name = "Market provider" if kind == "market" else "Options provider"
        self.base_url = settings.market_base_url if kind == "market" else settings.options_base_url
        self.key = settings.market_api_key if kind == "market" else settings.options_api_key
        self.capabilities = ["test", "backfill", "prices" if kind == "market" else "chain"]

    @property
    def configured(self) -> bool:
        url = urlsplit(self.base_url or "")
        return bool(
            url.scheme == "https"
            and url.hostname
            and not url.username
            and not url.password
            and not url.query
            and not url.fragment
        )

    async def read(
        self, symbol: str, start: str | date | None = None, end: str | date | None = None
    ) -> tuple[Response, list[dict[str, JsonValue]]]:
        if not self.configured or self.base_url is None:
            raise ProviderError(
                "Server-side HTTPS JSON adapter URL is not configured", "NOT_CONFIGURED"
            )
        params = {"symbol": symbol}
        if start:
            params["start"] = str(start)
        if end:
            params["end"] = str(end)
        response = await fetch(
            self.provider_name,
            self.base_url.rstrip("/") + ("/prices" if self.kind == "market" else "/options/chain"),
            headers={"Authorization": f"Bearer {self.key}"} if self.key else {},
            params=params,
            transport=self.transport,
        )
        payload = response.payload
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list) or not 1 <= len(rows) <= (
            100000 if self.kind == "market" else 2000
        ):
            raise ProviderError("Provider response requires a bounded nonempty rows array")
        validator = PriceObservation if self.kind == "market" else ChainContract
        normalized: list[dict[str, JsonValue]] = []
        seen: set[tuple[str, datetime]] = set()
        for row in rows:
            item = validator.model_validate(row)
            if item.symbol != symbol or item.timestamp > datetime.now(UTC):
                raise ProviderError("Provider row has the wrong symbol or a future timestamp")
            key = (
                item.option_symbol if isinstance(item, ChainContract) else symbol,
                item.timestamp,
            )
            if key in seen:
                raise ProviderError("Provider returned duplicate observation timestamps")
            seen.add(key)
            normalized.append(
                {
                    **item.model_dump(mode="json"),
                    **({"date": item.timestamp.isoformat()} if self.kind == "market" else {}),
                }
            )
        return response, normalized

    async def test(self) -> Response:
        response, _ = await self.read("SPY")
        return response
