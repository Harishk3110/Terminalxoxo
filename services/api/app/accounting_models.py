"""Valuation-owned accounting subledgers with source-record foreign keys."""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .schema import Base, IdMixin


class AccountingComponent(IdMixin, Base):
    __abstract__ = True
    valuation_run_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_valuation_runs.id"), nullable=False
    )
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    component_key: Mapped[str] = mapped_column(String(180), nullable=False)
    transaction_id: Mapped[str | None] = mapped_column(ForeignKey("portfolio_transactions.id"))
    account_id: Mapped[str | None] = mapped_column(ForeignKey("portfolio_accounts.id"))
    instrument_id: Mapped[str | None] = mapped_column(ForeignKey("instruments.id"))
    adjustment_id: Mapped[str | None] = mapped_column(
        ForeignKey("portfolio_balance_adjustments.id")
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    settlement_date: Mapped[date | None] = mapped_column(Date)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    native_amount: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    fx_rate: Mapped[Decimal | None] = mapped_column(Numeric(38, 16))
    base_amount: Mapped[Decimal | None] = mapped_column(Numeric(38, 16))
    capitalized_native: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    capitalized_base: Mapped[Decimal | None] = mapped_column(Numeric(38, 16))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


def component_constraints(
    name: str, kinds: tuple[str, ...], *, outstanding: bool = False
) -> tuple[Any, ...]:
    permitted = ", ".join(f"'{kind}'" for kind in kinds)
    constraints: list[Any] = [
        UniqueConstraint("valuation_run_id", "component_key", name=f"uq_{name}_run_key"),
        CheckConstraint(f"kind IN ({permitted})", name=f"ck_{name}_kind"),
        CheckConstraint("fx_rate IS NULL OR fx_rate > 0", name=f"ck_{name}_fx"),
        CheckConstraint(
            "settlement_date IS NULL OR settlement_date >= effective_date",
            name=f"ck_{name}_settlement",
        ),
        CheckConstraint("capitalized_native >= 0", name=f"ck_{name}_capitalized"),
        CheckConstraint(
            "(fx_rate IS NULL AND base_amount IS NULL AND capitalized_base IS NULL) OR "
            "(fx_rate IS NOT NULL AND base_amount IS NOT NULL AND capitalized_base IS NOT NULL)",
            name=f"ck_{name}_valuation",
        ),
        Index(f"ix_{name}_portfolio_date", "portfolio_id", "effective_date"),
    ]
    if outstanding:
        constraints.append(
            CheckConstraint(
                "(transaction_id IS NOT NULL AND adjustment_id IS NULL) OR "
                "(transaction_id IS NULL AND adjustment_id IS NOT NULL)",
                name=f"ck_{name}_source",
            )
        )
    else:
        constraints.append(
            CheckConstraint(
                "transaction_id IS NOT NULL AND adjustment_id IS NULL AND fx_rate IS NOT NULL AND base_amount IS NOT NULL",
                name=f"ck_{name}_source",
            )
        )
    return tuple(constraints)


class CapitalFlow(AccountingComponent):
    __tablename__ = "capital_flows"
    __table_args__ = component_constraints(
        "capital_flow", ("DEPOSIT", "WITHDRAWAL", "TRANSFER_IN", "TRANSFER_OUT")
    )


class PortfolioIncome(AccountingComponent):
    __tablename__ = "portfolio_income"
    __table_args__ = (
        *component_constraints("portfolio_income", ("DIVIDEND", "INTEREST")),
        CheckConstraint("native_amount > 0", name="ck_portfolio_income_positive"),
    )


class PortfolioFee(AccountingComponent):
    __tablename__ = "portfolio_fees"
    __table_args__ = (
        *component_constraints("portfolio_fee", ("COMMISSION", "FEE", "TAX")),
        CheckConstraint(
            "native_amount > 0 AND capitalized_native <= native_amount",
            name="ck_portfolio_fee_amount",
        ),
        CheckConstraint("kind != 'TAX' OR capitalized_native = 0", name="ck_portfolio_fee_tax"),
    )


class PortfolioAccrual(AccountingComponent):
    __tablename__ = "portfolio_accruals"
    __table_args__ = component_constraints(
        "portfolio_accrual", ("accrued_income", "receivables"), outstanding=True
    )


class PortfolioLiability(AccountingComponent):
    __tablename__ = "portfolio_liabilities"
    __table_args__ = component_constraints(
        "portfolio_liability", ("payables", "accrued_fees", "other_liabilities"), outstanding=True
    )
