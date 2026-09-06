"""Audited risk-limit configuration and durable breach/alert lifecycle, without actions."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .portfolio_operations import audit
from .portfolio_valuation import PortfolioValuationService

METRICS = {
    "max_position_weight",
    "top_five_concentration",
    "max_sector_weight",
    "max_country_weight",
    "max_currency_weight",
    "max_industry_weight",
    "gross_exposure",
    "net_exposure",
    "beta",
    "volatility",
    "var_loss_95",
    "cvar_loss_95",
    "drawdown_loss",
    "cash_weight",
    "leverage",
    "stale_exposure",
}


class LimitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    metric: str
    threshold: Decimal = Field(max_digits=18, decimal_places=8, allow_inf_nan=False)
    direction: Literal["MIN", "MAX"] = "MAX"
    enabled: bool = True
    reason: str = Field(min_length=10, max_length=2000)

    @field_validator("metric")
    @classmethod
    def supported(cls, value: str) -> str:
        if value not in METRICS:
            raise ValueError("Unsupported risk limit metric")
        return value


def metric_value(data, metric):
    nav = data.get("portfolio", {}).get("nav")
    if nav is None or not Decimal(str(nav)).is_finite() or Decimal(str(nav)) <= 0:
        return None
    source = {
        "var_loss_95": "var_95",
        "cvar_loss_95": "cvar_95",
        "drawdown_loss": "current_drawdown",
    }.get(metric, metric)
    value = data["risk"].get(source)
    if value is None:
        return None
    value = Decimal(str(value))
    if not value.is_finite():
        return None
    return abs(value) if source != metric else value


class RiskLimitService:
    def __init__(self, session: Session):
        self.session = session

    def rows(self, portfolio_id):
        return self.session.scalars(
            select(models.RiskLimit)
            .join(models.RiskPolicy)
            .where(
                models.RiskPolicy.portfolio_id == portfolio_id, models.RiskPolicy.enabled.is_(True)
            )
            .order_by(models.RiskLimit.metric)
        ).all()

    def configure(
        self, key: str, request: LimitRequest, actor: str | None, limit_id: str | None = None
    ):
        portfolio, profile = PortfolioValuationService(self.session).portfolio(key)
        self.session.execute(
            select(models.PortfolioProfile)
            .where(models.PortfolioProfile.id == profile.id)
            .with_for_update()
        ).scalar_one()
        row = (
            next((item for item in self.rows(portfolio.id) if item.id == limit_id), None)
            if limit_id
            else None
        )
        if limit_id and row is None:
            raise ValueError("Risk limit does not belong to the selected portfolio")
        before = (
            {"metric": row.metric, "threshold": str(row.threshold), "direction": row.direction}
            if row
            else None
        )
        if row is None:
            policy = self.session.scalar(
                select(models.RiskPolicy)
                .where(
                    models.RiskPolicy.portfolio_id == portfolio.id,
                    models.RiskPolicy.enabled.is_(True),
                )
                .limit(1)
            )
            if policy is None:
                policy = models.RiskPolicy(
                    portfolio_id=portfolio.id, name="Internal risk review", enabled=True
                )
                self.session.add(policy)
                self.session.flush()
            row = models.RiskLimit(policy_id=policy.id)
            self.session.add(row)
        row.metric, row.threshold, row.direction = (
            request.metric,
            request.threshold,
            request.direction,
        )
        self.session.flush()
        disabled = set(profile.configuration.get("disabled_risk_limit_ids", []))
        disabled.discard(row.id) if request.enabled else disabled.add(row.id)
        profile.configuration = {
            **profile.configuration,
            "disabled_risk_limit_ids": sorted(disabled),
        }
        audit(
            self.session,
            "RISK_LIMIT_CONFIGURED",
            "risk_limit",
            row.id,
            {
                "portfolio_id": portfolio.id,
                "before": before,
                "after": request.model_dump(mode="json"),
            },
            actor,
        )
        self.session.flush()
        return {"id": row.id, **request.model_dump(mode="json")}

    def evaluate(self, data, actor=None):
        portfolio_id = data["portfolio"]["id"]
        profile = self.session.execute(
            select(models.PortfolioProfile)
            .where(models.PortfolioProfile.portfolio_id == portfolio_id)
            .with_for_update()
        ).scalar_one()
        disabled = set(profile.configuration.get("disabled_risk_limit_ids", []))
        now = datetime.now(UTC)
        result = []
        for limit in self.rows(portfolio_id):
            value = metric_value(data, limit.metric)
            state = (
                "DISABLED"
                if limit.id in disabled
                else "NOT_EVALUATED"
                if value is None
                else "BREACH"
                if (
                    value > limit.threshold if limit.direction == "MAX" else value < limit.threshold
                )
                else "OK"
            )
            # One durable row per limit; transitions retain complete history in AuditLog.
            identifier = str(
                uuid.uuid5(uuid.NAMESPACE_URL, f"knk:risk-limit:{portfolio_id}:{limit.id}")
            )
            breach = self.session.get(models.RiskBreach, identifier)
            title = f"Risk limit [{limit.id}]"
            alert = self.session.scalar(
                select(models.Alert)
                .where(models.Alert.title == title)
                .order_by(models.Alert.created_at.desc())
                .limit(1)
            )
            previous = breach.state if breach else None
            previous_value = breach.observed_value if breach else None
            if state == "BREACH":
                if breach is None:
                    breach = models.RiskBreach(
                        id=identifier,
                        portfolio_id=portfolio_id,
                        limit_id=limit.id,
                        metric=limit.metric,
                        observed_value=value,
                        threshold=limit.threshold,
                        state="OPEN",
                    )
                    self.session.add(breach)
                breach.state, breach.observed_value, breach.threshold = (
                    "OPEN",
                    value,
                    limit.threshold,
                )
                breach.metric = limit.metric
                if alert is None or alert.state == "RESOLVED":
                    alert = models.Alert(
                        title=title,
                        severity="WARN",
                        state="OPEN",
                        message=f"{profile.code}: {limit.metric} {value} breaches {limit.direction} {limit.threshold}. Manual review required; no broker action.",
                    )
                    self.session.add(alert)
                alert.message = f"{profile.code}: {limit.metric} {value} breaches {limit.direction} {limit.threshold}. Manual review required; no broker action."
            elif breach is not None:
                breach.state = "UNDETERMINED" if state == "NOT_EVALUATED" else "RESOLVED"
                if breach.state == "RESOLVED" and alert is not None:
                    alert.state = "RESOLVED"
            if breach is not None:
                breach.updated_at = now
                if previous != breach.state:
                    audit(
                        self.session,
                        "RISK_BREACH_STATE_CHANGED",
                        "risk_breach",
                        breach.id,
                        {
                            "portfolio_id": portfolio_id,
                            "limit_id": limit.id,
                            "before": previous,
                            "after": breach.state,
                            "value": value,
                            "threshold": limit.threshold,
                            "valuation_run_id": data.get("valuation_run_id"),
                            "source": data.get("source"),
                            "as_of": data.get("as_of"),
                        },
                        actor,
                    )
                elif value is not None and value != previous_value:
                    audit(
                        self.session,
                        "RISK_BREACH_OBSERVATION",
                        "risk_breach",
                        breach.id,
                        {
                            "before": previous_value,
                            "after": value,
                            "valuation_run_id": data.get("valuation_run_id"),
                        },
                        actor,
                    )
            self.session.flush()
            result.append(
                {
                    "id": limit.id,
                    "metric": limit.metric,
                    "value": str(value) if value is not None else None,
                    "threshold": str(limit.threshold),
                    "direction": limit.direction,
                    "enabled": limit.id not in disabled,
                    "state": state,
                    "usage": float(value / limit.threshold)
                    if value is not None and limit.threshold
                    else None,
                    "severity": "WARN"
                    if state == "BREACH"
                    else "UNKNOWN"
                    if state == "NOT_EVALUATED"
                    else "INFO",
                    "first_breach": breach.created_at.isoformat() if breach else None,
                    "last_checked": now.isoformat(),
                    "breach_id": breach.id if breach else None,
                    "alert_id": alert.id if alert else None,
                }
            )
        return result

    def monitor(self, key, actor=None):
        data = PortfolioValuationService(self.session).latest(key, commit=False)
        limits = self.evaluate(data, actor)
        ids = [row["breach_id"] for row in limits if row["breach_id"]]
        history = self.session.scalars(
            select(models.AuditLog)
            .where(
                models.AuditLog.resource_type == "risk_breach", models.AuditLog.resource_id.in_(ids)
            )
            .order_by(models.AuditLog.created_at.desc())
            .limit(100)
        ).all()
        return {
            "portfolio": data["portfolio"],
            "risk": data["risk"],
            "model": data.get("risk_model", {}),
            "source": data["source"],
            "quality": data["quality"],
            "as_of": data["as_of"],
            "valuation_run_id": data["valuation_run_id"],
            "limits": limits,
            "timeline": [
                {
                    "id": row.id,
                    "timestamp": row.created_at.isoformat(),
                    "action": row.action,
                    **row.metadata_json,
                }
                for row in history
            ],
            "warnings": data["warnings"],
        }
