"""Portfolio-first API. All writes are ledger events; no brokerage execution routes."""

import io
import json
from datetime import UTC, date

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .database import get_session
from .portfolio_balances import BalanceAdjustmentRequest as BalanceRequest
from .portfolio_balances import PortfolioBalanceService
from .portfolio_operations import (
    PortfolioLedgerService,
    PortfolioReconciliationService,
    TradeMonitorService,
    audit,
)
from .portfolio_seed import reset_main_demo
from .portfolio_valuation import PortfolioValuationService, jsonable
from .price_sources import PRIORITY
from .transaction_context import TransactionContext

# Named defaults preserve direct-call signatures as well as FastAPI injection.
SESSION_DEPENDENCY = Depends(get_session)

router = APIRouter(prefix="/api/v1/operations")


def identity(request: Request, session: Session, admin: bool = False) -> str | None:
    from .terminal_api import auth_session

    user = auth_session(request, session)
    if not user["authenticated"] or admin and str(user.get("role", "")).upper() != "ADMIN":
        raise HTTPException(
            403, "Administrator access required" if admin else "Authentication required"
        )
    return session.scalar(select(models.User.id).where(models.User.email == user["email"]))


class LedgerRequest(TransactionContext):
    transaction_type: str
    trade_date: date
    settle_date: date | None = None
    symbol: str | None = None
    currency: str | None = None
    quantity: str = "0"
    price: str = "0"
    amount: str | None = None
    fee: str = "0"
    commission: str = "0"
    tax: str = "0"
    fx_rate_to_base: str | None = None
    contract_multiplier: str = "1"
    account_id: str | None = None
    notes: str | None = Field(default=None, max_length=10000)
    child_symbol: str | None = None
    metadata: dict = Field(default_factory=dict)


class ReviewRequest(BaseModel):
    state: str
    note: str = Field(min_length=1, max_length=10000)


@router.get("/portfolios")
def portfolios(session: Session = SESSION_DEPENDENCY):
    rows = session.execute(
        select(models.Portfolio, models.PortfolioProfile).join(
            models.PortfolioProfile, models.PortfolioProfile.portfolio_id == models.Portfolio.id
        )
    ).all()
    return {
        "items": [
            {
                "id": p.id,
                "code": profile.code,
                "name": p.name,
                "base_currency": p.base_currency,
                "is_default": p.is_default,
                "is_demo": profile.is_demo,
                "configuration": profile.configuration,
            }
            for p, profile in rows
        ]
    }


@router.get("/portfolio")
def summary(portfolio: str = "KNK_MAIN", view: str = "AUTO", session: Session = SESSION_DEPENDENCY):
    try:
        from .broker_api import account_view

        data = PortfolioValuationService(session).latest(portfolio)
        return data if view == "INTERNAL" else account_view(session, data)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/portfolio/recalculate")
def recalculate(portfolio: str = "KNK_MAIN", session: Session = SESSION_DEPENDENCY):
    return PortfolioValuationService(session).latest(portfolio, force=True)


@router.post("/transactions")
def add_transaction(
    payload: LedgerRequest,
    request: Request,
    portfolio: str = "KNK_MAIN",
    session: Session = SESSION_DEPENDENCY,
):
    try:
        result = PortfolioLedgerService(session).add(
            payload.model_dump(mode="json", exclude_none=True),
            portfolio,
            actor=identity(request, session),
        )
        session.commit()
        return result
    except (ValueError, IntegrityError) as exc:
        session.rollback()
        raise HTTPException(
            422 if isinstance(exc, ValueError) else 409,
            str(exc) if isinstance(exc, ValueError) else "Duplicate transaction reference",
        ) from exc


@router.get("/trades")
def trades(portfolio: str = "KNK_MAIN", session: Session = SESSION_DEPENDENCY):
    return {"items": TradeMonitorService(session).list(portfolio)}


@router.post("/trades/{trade_id}/review")
def review(
    trade_id: str, payload: ReviewRequest, request: Request, session: Session = SESSION_DEPENDENCY
):
    try:
        return TradeMonitorService(session).review(
            trade_id, payload.state, payload.note, identity(request, session)
        )
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.post("/reconciliation")
def reconcile(portfolio: str = "KNK_MAIN", session: Session = SESSION_DEPENDENCY):
    return PortfolioReconciliationService(session).reconcile(portfolio)


@router.post("/reconciliation/{break_id}/resolve")
def resolve_break(
    break_id: str, payload: ReviewRequest, request: Request, session: Session = SESSION_DEPENDENCY
):
    row = session.get(models.PortfolioReconciliationBreak, break_id)
    if row is None:
        raise HTTPException(404, "Break not found")
    if payload.state not in {"RESOLVED", "ACCEPTED", "OPEN"}:
        raise HTTPException(422, "Invalid resolution state")
    row.state, row.resolution = payload.state, payload.note
    audit(
        session,
        "RECONCILIATION_REVIEW",
        "reconciliation_break",
        row.id,
        payload.model_dump(),
        identity(request, session),
    )
    session.commit()
    return {"id": row.id, "state": row.state}


class ResetRequest(BaseModel):
    confirmation: str


@router.post("/reset-demo")
def reset(payload: ResetRequest, request: Request, session: Session = SESSION_DEPENDENCY):
    actor = identity(request, session, admin=True)
    if payload.confirmation != "RESET KNK_MAIN DEMO":
        raise HTTPException(422, "Explicit confirmation must be RESET KNK_MAIN DEMO")
    try:
        profile = reset_main_demo(session, actor=actor)
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc
    return {"status": "RESET", "portfolio_id": profile.id, "code": "KNK_MAIN"}


class SourceRequest(BaseModel):
    priority: list[str] = Field(default_factory=lambda: list(PRIORITY))
    preferred_source: str | None = None
    stale_after_hours: int = Field(default=72, ge=1, le=8760)
    reason: str = Field(min_length=5, max_length=1000)


@router.get("/sources/{symbol}")
def source_detail(symbol: str, session: Session = SESSION_DEPENDENCY):
    from datetime import datetime

    from .price_sources import MarketPriceResolver

    item = session.scalar(
        select(models.Instrument).where(models.Instrument.symbol == symbol.upper())
    )
    if item is None:
        raise HTTPException(404, "Unknown security")
    resolver = MarketPriceResolver(session, [item.id])
    now = datetime.now(UTC)
    rule = resolver.rules.get(item.id)
    return {
        "symbol": item.symbol,
        "selected": resolver.describe(item.id, now),
        "sources": [r.provenance(now) for r in resolver.candidates(item.id, now)],
        "rule": {
            "priority": rule.priority if rule else PRIORITY,
            "preferred_source": rule.preferred_source if rule else None,
            "stale_after_hours": rule.stale_after_hours if rule else 72,
            "reason": rule.reason if rule else "Default source precedence",
        },
    }


@router.post("/sources/{symbol}")
def source_rule(
    symbol: str, payload: SourceRequest, request: Request, session: Session = SESSION_DEPENDENCY
):
    item = session.scalar(
        select(models.Instrument).where(models.Instrument.symbol == symbol.upper())
    )
    if not item:
        raise HTTPException(404, "Unknown security")
    if len(payload.priority) != len(PRIORITY) or set(payload.priority) != set(PRIORITY):
        raise HTTPException(
            422, "Priority must contain BROKER, PROVIDER, FILE and DEMO exactly once"
        )
    row = session.scalar(
        select(models.SourcePrecedenceRule).where(
            models.SourcePrecedenceRule.instrument_id == item.id
        )
    )
    if not row:
        row = models.SourcePrecedenceRule(instrument_id=item.id)
        session.add(row)
    before = {"priority": row.priority, "preferred_source": row.preferred_source}
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    audit(
        session,
        "SOURCE_PRECEDENCE_CHANGED",
        "instrument",
        item.id,
        {"before": before, "after": payload.model_dump()},
        identity(request, session),
    )
    session.commit()
    return {"symbol": item.symbol, **payload.model_dump()}


@router.post("/balances")
def balance(
    payload: BalanceRequest,
    request: Request,
    portfolio: str = "KNK_MAIN",
    session: Session = SESSION_DEPENDENCY,
):
    try:
        result = PortfolioBalanceService(session).add(
            portfolio, payload, identity(request, session)
        )
        session.commit()
        return result
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


@router.get("/export")
def export_portfolio(portfolio: str = "KNK_MAIN", session: Session = SESSION_DEPENDENCY):
    from openpyxl import Workbook

    from .broker_api import account_view

    data = account_view(session, PortfolioValuationService(session).latest(portfolio))
    book = Workbook()
    book.remove(book.active)
    datasets = {
        "Summary": [data["portfolio"]],
        "Positions": data["positions"],
        "Cash": data["cash"],
        "Transactions": data["transactions"],
        "NAV History": data["curve"],
        "Performance": [data["performance"]],
        "Risk": [data["risk"]],
        "Attribution": data["attribution"],
        "Limits": data["breaches"],
        "Trade Monitor": TradeMonitorService(session).list(portfolio),
        "Reconciliation": [data["reconciliation"]],
        "Metadata": [
            {
                "source": data["source"],
                "as_of": data["as_of"],
                "calculated_at": data["calculated_at"],
                "version": data["calculation_version"],
                "method": data["methodology"],
                "quality": data["quality"],
                "warnings": data["warnings"],
            }
        ],
    }
    for name, rows in datasets.items():
        sheet = book.create_sheet(name)
        keys = list(dict.fromkeys(k for row in rows for k in row))
        sheet.append(keys or ["No records"])
        for row in rows:
            values = [
                json.dumps(jsonable(row.get(k)))
                if isinstance(row.get(k), (dict, list))
                else row.get(k)
                for k in keys
            ]
            sheet.append(values)
            for cell in sheet[sheet.max_row]:
                if isinstance(cell.value, str):
                    cell.data_type = "s"
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
    stream = io.BytesIO()
    book.save(stream)
    stream.seek(0)
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="KnK-Portfolio.xlsx"'},
    )
