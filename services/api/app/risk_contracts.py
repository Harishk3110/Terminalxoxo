"""Persisted valuation evidence and explicit risk-limit evaluation states."""

from collections.abc import Mapping
from decimal import Decimal
from typing import Annotated, Literal, TypedDict

from pydantic import BaseModel, Field, JsonValue, TypeAdapter

type RiskNumber = Annotated[Decimal, Field(allow_inf_nan=True)]
type LimitState = Literal["DISABLED", "NOT_EVALUATED", "BREACH", "OK"]


def disabled_limit_ids(configuration: Mapping[str, JsonValue]) -> set[str]:
    return set(
        TypeAdapter(list[str]).validate_python(
            configuration.get("disabled_risk_limit_ids", []),
            strict=True,
        )
    )


class RiskPortfolioInput(BaseModel):
    id: str | None = None
    nav: RiskNumber | None = None


class RiskSnapshotInput(BaseModel):
    portfolio: RiskPortfolioInput = Field(default_factory=RiskPortfolioInput)
    risk: dict[str, RiskNumber | None] = Field(default_factory=dict)
    valuation_run_id: str | None = None
    source: str | None = None
    as_of: str | None = None


class ConfiguredLimit(TypedDict):
    id: str
    metric: str
    threshold: str
    direction: Literal["MIN", "MAX"]
    enabled: bool
    reason: str


class LimitEvaluation(TypedDict):
    id: str
    metric: str
    value: str | None
    threshold: str
    direction: str
    enabled: bool
    state: LimitState
    usage: float | None
    severity: Literal["WARN", "UNKNOWN", "INFO"]
    first_breach: str | None
    last_checked: str
    breach_id: str | None
    alert_id: str | None


class MonitorEvidence(BaseModel):
    portfolio: dict[str, JsonValue]
    risk: dict[str, JsonValue]
    risk_model: dict[str, JsonValue] = Field(default_factory=dict)
    source: str
    quality: str
    as_of: str | None
    valuation_run_id: str
    warnings: list[str]


class RiskMonitorResult(TypedDict):
    portfolio: dict[str, JsonValue]
    risk: dict[str, JsonValue]
    model: dict[str, JsonValue]
    source: str
    quality: str
    as_of: str | None
    valuation_run_id: str
    limits: list[LimitEvaluation]
    timeline: list[dict[str, JsonValue]]
    warnings: list[str]
