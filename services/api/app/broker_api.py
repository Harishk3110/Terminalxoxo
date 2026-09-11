"""Read-only paper broker snapshots and explicitly approved fill-to-ledger imports."""

import hashlib
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import NotRequired, TypedDict

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, JsonValue, TypeAdapter, ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .data_drop_api import agent_auth, scope
from .database import get_session
from .portfolio_api import identity
from .portfolio_engine import decimal
from .portfolio_operations import PortfolioLedgerService, audit
from .portfolio_seed import profile_for
from .price_sources import utc

# Named defaults preserve direct-call signatures as well as FastAPI injection.
SESSION_DEPENDENCY = Depends(get_session)
AGENT_DEPENDENCY = Depends(agent_auth)

router = APIRouter()
JSON_OBJECT = TypeAdapter(dict[str, JsonValue])
TEXT = TypeAdapter(str)


class SnapshotReceipt(TypedDict):
    id: str
    duplicate: NotRequired[bool]
    status: NotRequired[str]
    fills_require_approval: NotRequired[bool]


class SnapshotView(TypedDict):
    state: str
    snapshot: dict[str, JsonValue] | None


class CashRecord(BaseModel):
    currency: str = Field(min_length=3, max_length=3)
    amount: str


class PositionRecord(BaseModel):
    symbol: str = Field(min_length=1, max_length=40)
    currency: str = Field(min_length=3, max_length=3)
    quantity: str
    average_cost: str
    multiplier: str = "1"
    market_price: str | None = None
    market_value_base: str | None = None


class FillRecord(BaseModel):
    execution_id: str = Field(min_length=1, max_length=160)
    symbol: str
    currency: str
    side: str
    contract_type: str = "STK"
    quantity: str
    price: str
    time: datetime
    commission: str | None = None
    commission_currency: str | None = None


class SnapshotRequest(BaseModel):
    account: str = Field(min_length=3, max_length=50)
    currency: str = Field(min_length=3, max_length=3)
    as_of: datetime
    nav: str
    cash: list[CashRecord] = Field(default_factory=list, max_length=50)
    positions: list[PositionRecord] = Field(default_factory=list, max_length=2000)
    fills: list[FillRecord] = Field(default_factory=list, max_length=10000)
    fx: dict[str, str] = Field(default_factory=dict)


class BrokerHoldings(BaseModel):
    cash: list[CashRecord] = Field(default_factory=list, max_length=50)
    positions: list[PositionRecord] = Field(default_factory=list, max_length=2000)
    fx: dict[str, str] = Field(default_factory=dict)


class RecordedFills(BaseModel):
    account_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    fills: list[FillRecord] = Field(default_factory=list, max_length=10000)


def complete_total(values: Sequence[Decimal | None]) -> str | None:
    if any(value is None for value in values):
        return None
    return str(sum((value for value in values if value is not None), Decimal(0)))


@router.post("/agent/v1/broker-snapshots")
def receive_snapshot(
    payload: SnapshotRequest,
    agent: models.LocalAgent = AGENT_DEPENDENCY,
    session: Session = SESSION_DEPENDENCY,
) -> SnapshotReceipt:
    scope(agent, "broker:read-sync")
    binding = next(
        (p.removeprefix("portfolio:") for p in agent.scopes if p.startswith("portfolio:")), None
    )
    portfolio = session.get(models.Portfolio, binding) if binding else None
    if not portfolio:
        raise HTTPException(403, "Agent has no portfolio binding")
    if not payload.account.startswith("DU") or payload.currency != portfolio.base_currency:
        raise HTTPException(422, "Paper account and matching declared base currency required")
    now = datetime.now(UTC)
    if abs((now - utc(payload.as_of)).total_seconds()) > 300:
        raise HTTPException(422, "Snapshot timestamp must be within five minutes")
    try:
        nav = decimal(payload.nav)
        for cash in payload.cash:
            decimal(cash.amount)
        for position in payload.positions:
            decimal(position.quantity)
            decimal(position.average_cost, nonnegative=True)
            decimal(position.multiplier, positive=True)
            if position.market_price is not None:
                decimal(position.market_price, positive=True)
        for fill in payload.fills:
            decimal(fill.quantity, positive=True)
            decimal(fill.price, positive=True)
            if fill.side not in {"BOT", "SLD", "BUY", "SELL"} or utc(fill.time) > now + timedelta(
                minutes=1
            ):
                raise ValueError("Invalid execution side or timestamp")
            if fill.commission is not None:
                decimal(fill.commission, nonnegative=True)
        for currency, rate in payload.fx.items():
            if len(currency) != 3:
                raise ValueError("Invalid FX currency")
            decimal(rate, positive=True)
        if payload.currency in payload.fx and decimal(payload.fx[payload.currency]) != 1:
            raise ValueError("Identity FX must equal one")
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    reference = hashlib.sha256(
        f"{agent.id}|{payload.account}|{payload.as_of.isoformat()}".encode()
    ).hexdigest()
    old = session.scalar(
        select(models.BrokerAccountSnapshot).where(
            models.BrokerAccountSnapshot.external_reference == reference
        )
    )
    if old:
        return {"id": old.id, "duplicate": True}
    account_hash = hashlib.sha256(payload.account.encode()).hexdigest()
    data = payload.model_dump(mode="json", exclude={"account"})
    data.update(
        {
            "agent_id": agent.id,
            "account_fingerprint": account_hash,
            "account_mask": "DU..." + payload.account[-3:],
            "mode": "PAPER",
        }
    )
    row = models.BrokerAccountSnapshot(
        portfolio_id=portfolio.id,
        external_reference=reference,
        as_of=utc(payload.as_of),
        source="IBKR PAPER",
        connected=True,
        nav=nav,
        currency=payload.currency,
        payload=data,
    )
    session.add(row)
    session.flush()
    for currency, rate in payload.fx.items():
        if currency != payload.currency:
            session.add(
                models.FxObservation(
                    base_currency=currency,
                    quote_currency=payload.currency,
                    timestamp=utc(payload.as_of),
                    rate=decimal(rate),
                    source="IBKR PAPER",
                    source_category="BROKER",
                    data_state="BROKER REPORTED",
                )
            )
    for position in payload.positions:
        item = session.scalar(
            select(models.Instrument).where(models.Instrument.symbol == position.symbol)
        )
        if (
            item
            and item.currency == position.currency
            and position.market_price
            and decimal(position.multiplier) == 1
        ):
            session.add(
                models.MarketObservation(
                    instrument_id=item.id,
                    timestamp=utc(payload.as_of),
                    price=decimal(position.market_price),
                    currency=item.currency,
                    source="IBKR PAPER",
                    source_category="BROKER",
                    data_state="BROKER REPORTED",
                    fields={
                        "snapshot_id": row.id,
                        "timestamp_basis": "Account snapshot; exchange quote timestamp not supplied",
                    },
                )
            )
    agent.last_seen = now
    agent.status = {
        **agent.status,
        "broker": "PAPER SNAPSHOT RECEIVED",
        "broker_as_of": payload.as_of.isoformat(),
    }
    audit(
        session,
        "BROKER_READ_ONLY_SNAPSHOT",
        "broker_snapshot",
        row.id,
        {
            "portfolio_id": portfolio.id,
            "agent_id": agent.id,
            "positions": len(payload.positions),
            "fills": len(payload.fills),
        },
    )
    session.commit()
    return {"id": row.id, "status": "STORED", "fills_require_approval": True}


def current_snapshot(
    session: Session, portfolio_id: str
) -> tuple[models.BrokerAccountSnapshot | None, bool]:
    row = session.scalar(
        select(models.BrokerAccountSnapshot)
        .where(models.BrokerAccountSnapshot.portfolio_id == portfolio_id)
        .order_by(models.BrokerAccountSnapshot.as_of.desc())
        .limit(1)
    )
    if row is None:
        return None, False
    agent_id = row.payload.get("agent_id")
    agent = session.get(models.LocalAgent, agent_id) if isinstance(agent_id, str) else None
    active = bool(
        agent
        and not agent.revoked_at
        and agent.last_seen
        and datetime.now(UTC) - utc(agent.last_seen) < timedelta(seconds=90)
        and datetime.now(UTC) - utc(row.as_of) < timedelta(seconds=90)
    )
    return row, active


@router.get("/api/v1/broker/snapshot")
def snapshot(session: Session = SESSION_DEPENDENCY) -> SnapshotView:
    profile = profile_for(session)
    if profile is None:
        return {"state": "NOT CONNECTED", "snapshot": None}
    row, active = current_snapshot(session, profile.portfolio_id)
    if row is None:
        return {"state": "NOT CONNECTED", "snapshot": None}
    return {
        "state": "CONNECTED READ ONLY" if active else "STALE / OFFLINE",
        "snapshot": {
            "id": row.id,
            "nav": str(row.nav),
            "currency": row.currency,
            "as_of": row.as_of.isoformat(),
            "source": row.source,
            **row.payload,
        },
    }


class ApproveFillRequest(BaseModel):
    snapshot_id: str
    execution_id: str
    transaction_type: str
    fx_rate_to_base: str
    rationale: str = Field(min_length=5, max_length=10000)


@router.post("/api/v1/broker/fills/import")
def approve_fill(
    payload: ApproveFillRequest, request: Request, session: Session = SESSION_DEPENDENCY
) -> dict[str, JsonValue]:
    actor = identity(request, session)
    row = session.get(models.BrokerAccountSnapshot, payload.snapshot_id)
    if row is None:
        raise HTTPException(404, "Recorded broker fill not found")
    try:
        recorded = RecordedFills.model_validate(row.payload)
    except ValidationError as exc:
        raise HTTPException(
            422, "Recorded broker fill data is invalid; reconciliation required"
        ) from exc
    fill = next(
        (fill for fill in recorded.fills if fill.execution_id == payload.execution_id),
        None,
    )
    if fill is None:
        raise HTTPException(404, "Recorded broker fill not found")
    if fill.contract_type != "STK":
        raise HTTPException(
            422,
            "Only mapped stock/ETF fills can enter this ledger; other contracts require reconciliation",
        )
    if fill.side not in {"BOT", "BUY", "SLD", "SELL"}:
        raise HTTPException(422, "Recorded execution side is invalid")
    allowed = {"BUY", "COVER"} if fill.side in {"BOT", "BUY"} else {"SELL", "SHORT"}
    if payload.transaction_type not in allowed:
        raise HTTPException(422, "Ledger type must match the recorded execution side")
    if fill.commission is None or fill.commission_currency not in {
        fill.currency,
        None,
    }:
        raise HTTPException(
            422,
            "A recorded commission in the execution currency is required; reconcile other-currency fees separately",
        )
    try:
        result = PortfolioLedgerService(session).add(
            {
                "transaction_type": payload.transaction_type,
                "trade_date": fill.time.date().isoformat(),
                "symbol": fill.symbol,
                "quantity": fill.quantity,
                "price": fill.price,
                "currency": fill.currency,
                "commission": fill.commission,
                "fx_rate_to_base": payload.fx_rate_to_base,
                "external_reference": recorded.account_fingerprint + ":" + fill.execution_id,
                "notes": payload.rationale,
                "metadata": {"broker_snapshot_id": row.id, "execution_id": fill.execution_id},
            },
            row.portfolio_id,
            source="IBKR PAPER",
            actor=actor,
        )
        output = JSON_OBJECT.validate_python(result, strict=True)
        session.commit()
        return output
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


def account_view(session: Session, internal: Mapping[str, object]) -> dict[str, JsonValue]:
    internal_json = JSON_OBJECT.validate_python(internal, strict=True)
    internal_portfolio = JSON_OBJECT.validate_python(internal_json["portfolio"], strict=True)
    portfolio_id = TEXT.validate_python(internal_portfolio["id"], strict=True)
    row, active = current_snapshot(session, portfolio_id)
    if row is None or not active:
        return {
            **internal_json,
            "broker_state": "NOT CONNECTED" if row is None else "STALE / OFFLINE",
            "account_source": "INTERNAL LEDGER",
        }
    holdings = BrokerHoldings.model_validate(row.payload)
    internal_performance = JSON_OBJECT.validate_python(internal_json["performance"], strict=True)
    internal_risk = JSON_OBJECT.validate_python(internal_json["risk"], strict=True)
    p = {
        key: internal_portfolio.get(key)
        for key in ("id", "code", "name", "base_currency", "execution_mode", "broker_mode")
    }
    data: dict[str, JsonValue] = {
        "portfolio": p,
        "performance": {key: None for key in internal_performance},
        "risk": {key: None for key in internal_risk},
        "transactions": [],
        "lots": [],
        "lot_matches": [],
        "cost_basis": None,
        "accounting": {"state": "UNAVAILABLE", "items": [], "totals": None, "reconciliation": None},
        "exposure_balances": [],
        "exposure_methodology": None,
        "valuation_run_id": None,
        "calculation_version": "BROKER SNAPSHOT",
        "calculated_at": None,
        "methodology": "Reported paper account snapshot; no internal ledger analytics",
    }
    for key in (
        "reference_capital",
        "opening_capital",
        "settled_cash",
        "available_cash",
        "settlement_receivables",
        "settlement_payables",
        "accounting_policy",
    ):
        p[key] = None
    p.update(
        {
            "nav": str(row.nav),
            "view": "BROKER REPORTED",
            "quality": "BROKER REPORTED",
            "as_of": row.as_of.isoformat(),
            "total_pnl": None,
            "total_return": None,
            "daily_pnl": None,
            "opening_nav": None,
        }
    )
    fx = {currency: decimal(rate, positive=True) for currency, rate in holdings.fx.items()}
    if row.currency in fx and fx[row.currency] != 1:
        raise ValueError("Recorded identity FX must equal one")
    fx[row.currency] = Decimal(1)
    cash: list[JsonValue] = []
    positions: list[JsonValue] = []
    cash_values: list[Decimal | None] = []
    position_values: list[Decimal | None] = []
    for c in holdings.cash:
        rate = fx.get(c.currency)
        amount = decimal(c.amount)
        base_value = amount * rate if rate is not None else None
        cash_values.append(base_value)
        cash.append(
            {
                **JSON_OBJECT.validate_python(c.model_dump(mode="json", exclude_unset=True)),
                "base_value": str(base_value) if base_value is not None else None,
                "fx_rate": str(rate) if rate is not None else None,
                "quality": "BROKER REPORTED",
                "source": row.source,
                "as_of": row.as_of.isoformat(),
            }
        )
    for pos in holdings.positions:
        item = session.scalar(
            select(models.Instrument).where(models.Instrument.symbol == pos.symbol)
        )
        rate = fx.get(pos.currency)
        quantity = decimal(pos.quantity)
        multiplier = decimal(pos.multiplier, positive=True)
        price = decimal(pos.market_price, positive=True) if pos.market_price is not None else None
        value = (
            quantity * price * rate * multiplier if price is not None and rate is not None else None
        )
        position_values.append(value)
        positions.append(
            {
                **JSON_OBJECT.validate_python(pos.model_dump(mode="json", exclude_unset=True)),
                "id": item.id if item else pos.symbol,
                "instrument_id": item.id if item else None,
                "name": item.name if item else pos.symbol,
                "sector": item.sector if item else "Unmapped",
                "country": item.country if item else "Unmapped",
                "asset_class": item.asset_class if item else "Unmapped",
                "weight": str(value / row.nav) if value is not None and row.nav else None,
                "market_value": str(value) if value is not None else None,
                "fx_rate": str(rate) if rate is not None else None,
                "unrealised_pnl": None,
                "realised_pnl": None,
                "daily_pnl": None,
                "total_pnl": None,
                "beta": None,
                "risk_contribution": None,
                "source": row.source,
                "as_of": row.as_of.isoformat(),
                "quality": "BROKER REPORTED",
            }
        )
    p["cash"] = complete_total(cash_values)
    p["market_value"] = complete_total(position_values)
    p["gross_asset_value"] = None
    for key in (
        "accrued_income",
        "receivables",
        "payables",
        "accrued_fees",
        "other_liabilities",
        "liabilities",
    ):
        p[key] = None
    data.update(
        {
            "positions": positions,
            "cash": cash,
            "curve": [],
            "correlation": {"symbols": [], "values": []},
            "monthly": [],
            "attribution": [],
            "exposures": {},
            "breaches": [],
            "source": row.source,
            "quality": "BROKER REPORTED",
            "as_of": row.as_of.isoformat(),
            "account_source": "BROKER",
            "broker_state": "CONNECTED READ ONLY",
            "broker_snapshot_id": row.id,
            "internal_ledger_nav": internal_portfolio["nav"],
            "reconciliation": {
                "state": "REQUIRES RECONCILIATION",
                "internal_nav": internal_portfolio["nav"],
                "broker_nav": str(row.nav),
            },
            "metric_metadata": {},
            "freshness": {
                "price_coverage_pct": sum(
                    pos.market_price is not None for pos in holdings.positions
                )
                / len(holdings.positions)
                * 100
                if positions
                else 100,
                "stale_nav_pct": None,
            },
            "warnings": [
                "Authoritative current NAV is broker-reported. Internal ledger NAV is retained separately for reconciliation.",
                "Broker-history P&L, performance and risk are unavailable in this view. Explicit INTERNAL ledger analytics remain separate and do not describe this broker account.",
                "Account snapshot timestamps are not exchange quote timestamps. No order transmission is available.",
            ],
        }
    )
    return data
