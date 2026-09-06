"""Validated, append-only accrual and liability adjustments with dated roll-forward."""

from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .ledger_contracts import RevisionRequest
from .portfolio_domain.money import ZERO, decimal
from .portfolio_operations import CURRENCIES, audit
from .portfolio_valuation import PortfolioValuationService


class BalanceAdjustmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    effective_date: date
    bucket: Literal[
        "accrued_income", "receivables", "payables", "accrued_fees", "other_liabilities"
    ]
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    amount: Decimal
    reason: str = Field(min_length=5, max_length=1000)

    @field_validator("amount")
    @classmethod
    def representable_amount(cls, value: Decimal) -> Decimal:
        value = decimal(value, "adjustment amount")
        if value == ZERO or value != value.quantize(Decimal(".00000001")):
            raise ValueError("Balance adjustment must be nonzero with at most eight decimal places")
        return value

    @field_validator("reason")
    @classmethod
    def meaningful_reason(cls, value: str) -> str:
        return RevisionRequest.meaningful_reason(value)


class PortfolioBalanceService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, portfolio_id: str) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(models.PortfolioBalanceAdjustment)
            .where(
                models.PortfolioBalanceAdjustment.portfolio_id == portfolio_id,
            )
            .order_by(
                models.PortfolioBalanceAdjustment.effective_date,
                models.PortfolioBalanceAdjustment.id,
            )
        ).all()
        return [
            {
                "id": row.id,
                "effective_date": row.effective_date.isoformat(),
                "bucket": row.bucket,
                "currency": row.currency,
                "amount": str(row.amount),
                "reason": row.reason,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]

    def add(self, key: str, request: BalanceAdjustmentRequest, actor: str | None) -> dict[str, Any]:
        portfolio, _ = PortfolioValuationService(self.session).portfolio(key)
        # Serialize balance writers for a portfolio on databases supporting row locks.
        self.session.scalar(
            select(models.Portfolio).where(models.Portfolio.id == portfolio.id).with_for_update()
        )
        if request.effective_date > datetime.now(UTC).date():
            raise ValueError("Future balance adjustments are not accepted")
        if request.currency not in CURRENCIES:
            raise ValueError("Balance currency is not configured")
        opening = self.session.scalar(
            select(models.PortfolioTransaction.trade_date)
            .where(
                models.PortfolioTransaction.portfolio_id == portfolio.id,
            )
            .order_by(models.PortfolioTransaction.trade_date)
            .limit(1)
        )
        if opening is None or request.effective_date < opening:
            raise ValueError("Balance adjustment cannot precede the portfolio ledger")
        records = self.session.scalars(
            select(models.PortfolioBalanceAdjustment).where(
                models.PortfolioBalanceAdjustment.portfolio_id == portfolio.id,
                models.PortfolioBalanceAdjustment.bucket == request.bucket,
                models.PortfolioBalanceAdjustment.currency == request.currency,
            )
        ).all()
        changes: dict[date, Decimal] = defaultdict(Decimal)
        for record in records:
            changes[record.effective_date] += record.amount
        changes[request.effective_date] += request.amount
        running = ZERO
        for day in sorted(changes):
            running += changes[day]
            if running < ZERO:
                raise ValueError(
                    f"Adjustment makes {request.bucket} in {request.currency} negative on {day}"
                )
        row = models.PortfolioBalanceAdjustment(portfolio_id=portfolio.id, **request.model_dump())
        self.session.add(row)
        self.session.flush()
        audit(
            self.session,
            "NAV_BALANCE_ADJUSTED",
            "portfolio_balance",
            row.id,
            {"portfolio_id": portfolio.id, **request.model_dump(mode="json")},
            actor,
        )
        self.session.flush()
        return {
            "id": row.id,
            "portfolio_id": portfolio.id,
            "created_at": row.created_at.isoformat(),
            **request.model_dump(mode="json"),
        }
