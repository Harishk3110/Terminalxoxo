"""Normalized option observations; file provenance does not establish dealer inventory."""

from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class ChainContract(BaseModel):
    model_config = ConfigDict(extra="ignore", allow_inf_nan=False)
    symbol: str = Field(min_length=1, max_length=40)
    option_symbol: str = Field(min_length=1, max_length=120)
    expiry: date
    expiry_time_utc: time = time(20)
    strike: float = Field(gt=0, le=1e9)
    right: Literal["CALL", "PUT"]
    multiplier: float = Field(gt=0, le=1e6)
    exercise_style: Literal["EUROPEAN", "AMERICAN"]
    currency: str = Field(min_length=3, max_length=3)
    timestamp: datetime
    iv_unit: Literal["DECIMAL", "PERCENT"]
    iv: float | None = Field(default=None, gt=0, le=500)
    bid: float | None = Field(default=None, ge=0, le=1e9)
    ask: float | None = Field(default=None, ge=0, le=1e9)
    last: float | None = Field(default=None, ge=0, le=1e9)
    volume: int | None = Field(default=None, ge=0, le=10**12)
    open_interest: int | None = Field(default=None, ge=0, le=10**12)
    oi_change: int | None = Field(default=None, ge=-(10**12), le=10**12)
    delta: float | None = Field(default=None, ge=-1, le=1)
    gamma: float | None = Field(default=None, ge=0)
    theta: float | None = None
    vega: float | None = Field(default=None, ge=0)
    rho: float | None = None
    greek_units: Literal["STANDARD", "UNSPECIFIED"] = "UNSPECIFIED"

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.timestamp.tzinfo is None:
            raise ValueError("Chain timestamp requires an explicit timezone")
        if self.expiry_time_utc.tzinfo is not None:
            raise ValueError("Expiry time is an unzoned clock time explicitly interpreted as UTC")
        if self.bid is not None and self.ask is not None and self.ask < self.bid:
            raise ValueError("Crossed option bid/ask")
        if self.iv is not None and self.iv_unit == "DECIMAL" and self.iv > 5:
            raise ValueError("Decimal implied volatility exceeds 500%; check units")
        if self.right == "CALL" and self.delta is not None and self.delta < 0:
            raise ValueError("Call delta cannot be negative")
        if self.right == "PUT" and self.delta is not None and self.delta > 0:
            raise ValueError("Put delta cannot be positive")
        return self

    @property
    def expires_at(self) -> datetime:
        return datetime.combine(self.expiry, self.expiry_time_utc, UTC)

    @property
    def volatility(self) -> float | None:
        return self.iv / (100 if self.iv_unit == "PERCENT" else 1) if self.iv is not None else None


def normalize_option(row: Mapping[str, object]) -> dict[str, JsonValue]:
    values = {key: value for key, value in row.items() if value not in (None, "")}
    for key in ("symbol", "right", "exercise_style", "currency", "iv_unit", "greek_units"):
        if key in values:
            values[key] = str(values[key]).strip().upper()
    right = values.get("right")
    if isinstance(right, str):
        values["right"] = {"C": "CALL", "P": "PUT"}.get(right, right)
    contract = ChainContract.model_validate(values)
    if contract.timestamp > datetime.now(UTC):
        raise ValueError("Option timestamp cannot be in the future")
    return contract.model_dump(mode="json")
