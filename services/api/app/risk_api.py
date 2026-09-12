"""Authenticated internal risk monitoring and administrator-controlled review limits."""

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from .hedge_engine import HedgeRequest, HedgeService
from .portfolio_api import identity
from .portfolio_operations import audit
from .portfolio_resource_api import Database
from .portfolio_valuation import PortfolioValuationService
from .risk_contracts import ConfiguredLimit, RiskMonitorResult
from .risk_limits import LimitRequest, RiskLimitService
from .risk_statistics import RiskSettings

router = APIRouter(prefix="/api/v1/risk/portfolios", tags=["risk-monitor"])


@router.post("/{portfolio}/hedges", status_code=201)
def create_hedge(portfolio: str, payload: HedgeRequest, request: Request, session: Database):
    return HedgeService(session).create(portfolio, payload, identity(request, session))


class HedgeReviewRequest(BaseModel):
    state: Literal["DRAFT", "REVIEWED", "ACCEPTED MANUALLY", "REJECTED"]
    reason: str = Field(min_length=10, max_length=2000)


@router.post("/{portfolio}/hedges/{run_id}/review")
def review_hedge(
    portfolio: str, run_id: str, payload: HedgeReviewRequest, request: Request, session: Database
):
    return HedgeService(session).review(
        portfolio, run_id, payload.state, payload.reason, identity(request, session)
    )


@router.get("/{portfolio}/monitor")
def monitor(portfolio: str, request: Request, session: Database) -> RiskMonitorResult:
    return RiskLimitService(session).monitor(portfolio, identity(request, session))


@router.post("/{portfolio}/limits", status_code=201)
def create_limit(
    portfolio: str,
    payload: LimitRequest,
    request: Request,
    session: Database,
) -> ConfiguredLimit:
    return RiskLimitService(session).configure(
        portfolio, payload, identity(request, session, admin=True)
    )


@router.post("/{portfolio}/limits/{limit_id}")
def update_limit(
    portfolio: str, limit_id: str, payload: LimitRequest, request: Request, session: Database
) -> ConfiguredLimit:
    return RiskLimitService(session).configure(
        portfolio, payload, identity(request, session, admin=True), limit_id
    )


class RiskSettingsRequest(RiskSettings):
    reason: str = Field(min_length=10, max_length=2000)


@router.post("/{portfolio}/settings")
def update_settings(
    portfolio: str, payload: RiskSettingsRequest, request: Request, session: Database
):
    actor = identity(request, session, admin=True)
    book, profile = PortfolioValuationService(session).portfolio(portfolio)
    before = profile.configuration.get("risk_settings", {})
    settings = payload.model_dump(exclude={"reason"})
    profile.configuration = {**profile.configuration, "risk_settings": settings}
    audit(
        session,
        "RISK_SETTINGS_UPDATED",
        "portfolio",
        book.id,
        {"before": before, "after": settings, "reason": payload.reason},
        actor,
    )
    session.flush()
    return settings
