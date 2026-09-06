"""Persist and query immutable accounting detail for a selected valuation run."""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .accounting_models import (
    AccountingComponent,
    CapitalFlow,
    PortfolioAccrual,
    PortfolioFee,
    PortfolioIncome,
    PortfolioLiability,
)
from .portfolio_domain.postings import PostingCategory

COMPONENT_MODELS: dict[PostingCategory, type[AccountingComponent]] = {
    PostingCategory.CAPITAL: CapitalFlow,
    PostingCategory.INCOME: PortfolioIncome,
    PostingCategory.FEE: PortfolioFee,
    PostingCategory.ACCRUAL: PortfolioAccrual,
    PostingCategory.LIABILITY: PortfolioLiability,
}


def persist_accounting(
    session: Session, portfolio_id: str, run_id: str, rows: list[dict[str, Any]]
) -> None:
    for row in rows:
        model = COMPONENT_MODELS[PostingCategory(row["category"])]
        session.add(
            model(
                valuation_run_id=run_id,
                portfolio_id=portfolio_id,
                component_key=row["key"],
                transaction_id=row["transaction_id"],
                account_id=row["account_id"],
                instrument_id=row["instrument_id"],
                adjustment_id=row["adjustment_id"],
                kind=row["kind"],
                effective_date=date.fromisoformat(row["effective_date"]),
                settlement_date=date.fromisoformat(row["settlement_date"])
                if row["settlement_date"]
                else None,
                currency=row["currency"],
                native_amount=Decimal(row["native_amount"]),
                fx_rate=Decimal(row["fx_rate"]) if row["fx_rate"] is not None else None,
                base_amount=Decimal(row["base_amount"]) if row["base_amount"] is not None else None,
                capitalized_native=Decimal(row["capitalized_native"]),
                capitalized_base=Decimal(row["capitalized_base"])
                if row["capitalized_base"] is not None
                else None,
                payload=row,
            )
        )
    session.flush()


def accounting_records(
    session: Session,
    portfolio_id: str,
    run_id: str,
    category: PostingCategory | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for kind, model in COMPONENT_MODELS.items():
        if category is not None and kind != category:
            continue
        records = session.scalars(
            select(model).where(
                model.portfolio_id == portfolio_id,
                model.valuation_run_id == run_id,
            )
        ).all()
        rows.extend(
            {**record.payload, "id": record.id, "valuation_run_id": run_id} for record in records
        )
    return sorted(rows, key=lambda row: (row["effective_date"], row["key"]), reverse=True)
