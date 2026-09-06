"""Typed settings and immutable inputs for portfolio performance analysis."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Frequency(StrEnum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class FeeBasis(StrEnum):
    NET = "NET"
    GROSS = "GROSS"


class PerformanceSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    start: date | None = None
    end: date | None = None
    frequency: Frequency = Frequency.DAILY
    fee_basis: FeeBasis = FeeBasis.NET
    risk_free_rate: Decimal = Field(default=Decimal(0), gt=-1, le=1, allow_inf_nan=False)
    trading_days: int = Field(default=252, ge=200, le=366, strict=True)
    minimum_observations: int = Field(default=60, ge=2, le=1000, strict=True)
    rolling_window: int = Field(default=60, ge=2, le=1260, strict=True)

    @model_validator(mode="after")
    def ordered_range(self) -> "PerformanceSettings":
        if self.start and self.end and self.start > self.end:
            raise ValueError("Performance start must not follow end")
        return self

    @property
    def periods_per_year(self) -> int:
        return {Frequency.DAILY: self.trading_days, Frequency.WEEKLY: 52, Frequency.MONTHLY: 12}[
            self.frequency
        ]


@dataclass(frozen=True)
class ReturnObservation:
    day: date
    net_return: Decimal | None
    opening_nav: Decimal | None
    closing_nav: Decimal | None
    external_flow: Decimal | None
    daily_pnl: Decimal | None
    fee_expense: Decimal | None = None
    benchmark_return: Decimal | None = None
    quality: str = "CALCULATED"

    def __post_init__(self) -> None:
        for name in (
            "net_return",
            "opening_nav",
            "closing_nav",
            "external_flow",
            "daily_pnl",
            "fee_expense",
            "benchmark_return",
        ):
            value = getattr(self, name)
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite()):
                raise ValueError(f"{name} must be a finite Decimal or unavailable")

    def selected_return(self, basis: FeeBasis) -> tuple[Decimal | None, str | None]:
        if self.net_return is None:
            return None, "Missing or invalid NAV return"
        if self.net_return < -1:
            return None, "Return below -100% cannot be geometrically linked"
        if basis == FeeBasis.NET:
            return self.net_return, None
        if self.fee_expense is None:
            return None, "Fee expense was not recorded for this observation"
        if self.opening_nav is None or self.external_flow is None:
            return None, "Opening capital or external flow is unavailable"
        capital = self.opening_nav + self.external_flow
        if capital <= 0:
            return None, "Beginning-of-period invested capital is not positive"
        gross = self.net_return + self.fee_expense / capital
        if gross < -1:
            return None, "Gross return below -100% cannot be geometrically linked"
        return gross, None


@dataclass(frozen=True)
class ReturnPeriod:
    start: date
    end: date
    value: Decimal | None
    benchmark: Decimal | None
    observations: int
    missing: int
    reason: str | None = None


@dataclass(frozen=True)
class MetricResult:
    value: float | int | str | None
    state: str
    observations: int
    reason: str | None = None
    unit: str = "RETURN"

    @classmethod
    def unavailable(cls, count: int, reason: str, unit: str = "RETURN") -> "MetricResult":
        return cls(None, "INSUFFICIENT_DATA", count, reason, unit)
