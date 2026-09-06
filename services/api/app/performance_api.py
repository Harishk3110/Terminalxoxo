"""Private portfolio performance views and audited immutable calculation requests."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .performance_domain.contracts import FeeBasis, Frequency, PerformanceSettings
from .portfolio_api import identity
from .portfolio_performance import PortfolioPerformanceService
from .portfolio_resource_api import Database

router = APIRouter(prefix="/api/v1/performance/portfolios", tags=["performance"])
PerformanceView = Literal["summary", "series", "drawdowns", "monthly", "rolling", "report"]


def query_settings(
    start: date | None = None,
    end: date | None = None,
    frequency: Frequency = Frequency.DAILY,
    fee_basis: FeeBasis = FeeBasis.NET,
    risk_free_rate: Annotated[Decimal, Query(gt=-1, le=1)] = Decimal(0),
    trading_days: Annotated[int, Query(ge=200, le=366)] = 252,
    minimum_observations: Annotated[int, Query(ge=2, le=1000)] = 60,
    rolling_window: Annotated[int, Query(ge=2, le=1260)] = 60,
) -> PerformanceSettings:
    try:
        return PerformanceSettings(
            start=start,
            end=end,
            frequency=frequency,
            fee_basis=fee_basis,
            risk_free_rate=risk_free_rate,
            trading_days=trading_days,
            minimum_observations=minimum_observations,
            rolling_window=rolling_window,
        )
    except ValidationError as exc:
        raise HTTPException(422, "Invalid performance settings or date range") from exc


SettingsQuery = Annotated[PerformanceSettings, Depends(query_settings)]


class CalculatePerformanceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    settings: PerformanceSettings = Field(default_factory=PerformanceSettings)
    valuation_run_id: str | None = Field(default=None, min_length=1, max_length=100)


@router.post("/{portfolio_id}/calculate", status_code=201)
def calculate(
    portfolio_id: str,
    payload: CalculatePerformanceRequest,
    request: Request,
    session: Database,
) -> dict[str, Any]:
    return PortfolioPerformanceService(session).save(
        portfolio_id,
        payload.settings,
        payload.valuation_run_id,
        identity(request, session),
    )


@router.get("/{portfolio_id}/runs/{run_id}")
def saved(portfolio_id: str, run_id: str, session: Database) -> dict[str, Any]:
    return PortfolioPerformanceService(session).saved(portfolio_id, run_id)


@router.get("/{portfolio_id}/{view}")
def performance_view(
    portfolio_id: str,
    view: PerformanceView,
    settings: SettingsQuery,
    session: Database,
    valuation_run_id: str | None = None,
) -> dict[str, Any]:
    result = PortfolioPerformanceService(session).calculate(
        portfolio_id, settings, valuation_run_id
    )
    return {
        key: value
        for key, value in result.items()
        if view == "report"
        or key not in {"summary", "series", "drawdowns", "monthly", "rolling"}
        or key == view
    }
