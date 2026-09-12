"""Application services for ledger writes, trade review and reference/broker reconciliation."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .equity_contracts import finite_object
from .ledger_storage import validate_storage
from .portfolio_domain.money import money, stored_decimal
from .portfolio_domain.transaction_cash import enrich_cash_effects
from .portfolio_domain.types import AccountingPolicy
from .portfolio_engine import TRANSACTION_TYPES, LedgerState, decimal
from .portfolio_valuation import PortfolioValuationService, jsonable, load_entries
from .price_sources import FxRateResolver, MarketPriceResolver, close_of_day
from .reconciliation_contracts import (
    BOOK,
    BROKER,
    HEADER,
    BreakType,
    EffectiveTransaction,
    PositionAmount,
    ReconciliationItem,
    ReconciliationResult,
)
from .trade_monitor_contracts import (
    LEGACY_CONTEXT_FIELDS,
    METADATA,
    MONITOR_ROW,
    REVIEW_RECEIPT,
    TRADE_RISK,
    TRADE_TEXT,
    TRANSACTIONS,
    TradeMonitorRow,
    TradeReviewReceipt,
    position_weight,
    sector_weight,
    trade_risk_snapshot,
)
from .transaction_context import record_context
from .transaction_views import transaction_views

CURRENCIES = {"SGD", "USD", "EUR", "GBP", "JPY", "HKD", "AUD", "CAD", "CHF", "CNH", "CNY", "NZD"}


def audit(
    session: Session,
    action: str,
    resource_type: str,
    resource_id: str,
    metadata: dict[str, Any],
    actor: str | None = None,
) -> None:
    session.add(
        models.AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            actor_user_id=actor,
            correlation_id=str(uuid.uuid4()),
            metadata_json=jsonable(metadata),
        )
    )


class PortfolioLedgerService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.valuation = PortfolioValuationService(session)

    def add(
        self,
        payload: dict[str, Any],
        portfolio_key: str | None = None,
        *,
        source: str = "MANUAL",
        source_file_id: str | None = None,
        actor: str | None = None,
    ) -> dict[str, Any]:
        portfolio, profile = self.valuation.portfolio(portfolio_key)
        kind = str(payload.get("transaction_type", "")).upper()
        if kind not in TRANSACTION_TYPES:
            raise ValueError("Unknown transaction type")
        day = date.fromisoformat(str(payload.get("trade_date", ""))[:10])
        if day > datetime.now(UTC).date():
            raise ValueError("Future-dated ledger transactions are not accepted")
        settle = date.fromisoformat(str(payload.get("settle_date") or day.isoformat())[:10])
        if settle < day:
            raise ValueError("Settlement date cannot precede trade date")
        instrument = None
        if payload.get("symbol"):
            instrument = self.session.scalar(
                select(models.Instrument).where(
                    models.Instrument.symbol == str(payload["symbol"]).upper()
                )
            )
            if not instrument:
                raise ValueError("Unknown security; map the instrument before import")
        currency = str(
            payload.get("currency")
            or (instrument.currency if instrument else portfolio.base_currency)
        ).upper()
        if currency not in CURRENCIES or instrument and currency != instrument.currency:
            raise ValueError("Unsupported currency or currency does not match instrument")
        if kind == "SHORT" and not profile.configuration.get("allow_short", False):
            raise ValueError("Short positions are disabled in this portfolio policy")
        quantity = stored_decimal(payload.get("quantity", 0), "quantity", nonnegative=True)
        price = stored_decimal(payload.get("price", 0), "price", nonnegative=True)
        fee = stored_decimal(payload.get("fee", 0), "fee", nonnegative=True)
        commission = stored_decimal(payload.get("commission", 0), "commission", nonnegative=True)
        tax = stored_decimal(payload.get("tax", 0), "tax", nonnegative=True)
        multiplier = stored_decimal(
            payload.get("contract_multiplier", 1), "multiplier", positive=True
        )
        amount = stored_decimal(
            payload.get("amount") or payload.get("gross_amount") or quantity * price * multiplier,
            "gross amount",
            nonnegative=True,
        )
        if kind in {"BUY", "SELL", "SHORT", "COVER"} and amount != quantity * price * multiplier:
            raise ValueError("Gross amount must equal quantity times price times multiplier")
        if kind in {"COMMISSION", "FEE", "TAX"} and amount and fee + commission + tax:
            raise ValueError("Supply one expense amount, not both amount and charge fields")
        if currency == portfolio.base_currency:
            fx = Decimal("1")
            if (
                payload.get("fx_rate_to_base") is not None
                and decimal(payload["fx_rate_to_base"]) != 1
            ):
                raise ValueError("Base-currency FX must equal one")
            fx_source = "IDENTITY"
        elif payload.get("fx_rate_to_base") is not None:
            fx = stored_decimal(payload["fx_rate_to_base"], "transaction FX", positive=True)
            fx_source = "USER PROVIDED TRANSACTION FX"
        else:
            resolved_fx, provenance = FxRateResolver(self.session).resolve(
                currency, portfolio.base_currency, close_of_day(day)
            )
            if resolved_fx is None:
                raise ValueError(
                    "Missing transaction FX; supply an explicit recorded exchange rate"
                )
            fx = resolved_fx
            fx_source = provenance["source"]
        metadata = dict(payload.get("metadata") or {})
        metadata.pop("fx_recording", None)
        if currency != portfolio.base_currency and payload.get("fx_rate_to_base") is None:
            observed_fx = fx
            fx = stored_decimal(money(fx, 8), "recorded transaction FX", positive=True)
            metadata["fx_recording"] = {
                "observed_rate": str(observed_fx),
                "recorded_rate": str(fx),
                "rounding": "ROUND_HALF_EVEN",
                "decimal_places": 8,
            }
        stored_base_value = money(amount * fx, 8)
        stored_decimal(stored_base_value, "stored base value", nonnegative=True)
        validate_storage(
            self.session,
            {
                "quantity": quantity,
                "price": price,
                "fee": fee,
                "commission": commission,
                "tax": tax,
                "multiplier": multiplier,
                "gross amount": amount,
                "transaction FX": fx,
                "stored base value": stored_base_value,
            },
        )
        for key in (
            "to_currency",
            "to_amount",
            "ratio",
            "cost_allocation",
            "exchange_ratio",
            "cash_per_share",
            "cash_cost_allocation",
            "reason",
            "direction",
            "thesis_id",
            "strategy_id",
            "rationale",
        ):
            if payload.get(key) is not None:
                metadata[key] = payload[key]
        context = record_context(payload, metadata, day)
        notes = TRADE_TEXT.validate_python(payload.get("notes"), strict=True)
        rationale = TRADE_TEXT.validate_python(metadata.get("rationale"), strict=True) or notes
        if kind == "FX_CONVERSION":
            if str(metadata.get("to_currency", "")).upper() not in CURRENCIES:
                raise ValueError("FX destination currency is unknown")
            metadata["to_currency"] = str(metadata["to_currency"]).upper()
        if kind in {"SPINOFF", "MERGER"}:
            child = self.session.scalar(
                select(models.Instrument).where(
                    models.Instrument.symbol == str(payload.get("child_symbol", "")).upper()
                )
            )
            if not child or not instrument or child.currency != instrument.currency:
                raise ValueError(
                    "Corporate action requires a known child security in the parent currency"
                )
            metadata["child_instrument_id"] = child.id
        for link, model in (
            ("thesis_id", models.InvestmentThesis),
            ("strategy_id", models.StrategyDefinition),
        ):
            if metadata.get(link) and self.session.get(model, metadata[link]) is None:
                raise ValueError(f"Unknown {link}")
        metadata["fx_source"] = fx_source
        reference = context.external_reference
        external_key = (
            hashlib.sha256(f"{portfolio.id}|{source}|{reference}".encode()).hexdigest()
            if reference
            else None
        )
        if external_key:
            old = self.session.scalar(
                select(models.TransactionDetail).where(
                    models.TransactionDetail.external_key == external_key
                )
            )
            if old:
                return {"duplicate": True, "id": old.transaction_id}
        account_id = payload.get("account_id")
        if account_id:
            account = self.session.get(models.PortfolioAccount, account_id)
            if not account or account.portfolio_id != portfolio.id:
                raise ValueError("Account does not belong to portfolio")
        else:
            account_id = self.session.scalar(
                select(models.PortfolioAccount.id)
                .where(models.PortfolioAccount.portfolio_id == portfolio.id)
                .limit(1)
            )
        existing, _ = load_entries(self.session, portfolio.id)
        start = min((e.day for e in existing), default=day)
        before = self.valuation.calculate(portfolio.id, day) if existing and day >= start else None
        txn = models.PortfolioTransaction(
            portfolio_id=portfolio.id,
            account_id=account_id,
            instrument_id=instrument.id if instrument else None,
            transaction_type=kind,
            trade_date=day,
            settle_date=settle,
            quantity=quantity,
            price=price,
            currency=currency,
            fx_rate_to_base=fx,
            fee=fee,
            source=source,
            quality="USER PROVIDED" if source_file_id else "INTERNAL LEDGER",
            notes=notes,
        )
        self.session.add(txn)
        self.session.flush()
        detail = models.TransactionDetail(
            transaction_id=txn.id,
            gross_amount=amount,
            commission=commission,
            tax=tax,
            contract_multiplier=multiplier,
            base_value=stored_base_value,
            external_key=external_key,
            source_file_id=source_file_id,
            metadata_json=jsonable({**metadata, "external_reference": reference}),
            reconciliation_state="MATCHED" if source == "IBKR PAPER" else "INTERNAL_ONLY",
        )
        self.session.add(detail)
        self.session.flush()
        # Validate the full chronological ledger, including effects on later trades.
        entries, _ = load_entries(self.session, portfolio.id)
        state = LedgerState(policy=AccountingPolicy.from_config(profile.configuration))
        for entry in entries:
            state.apply(entry)
        after = self.valuation.calculate(portfolio.id, day)
        event = models.TradeEvent(
            portfolio_id=portfolio.id,
            transaction_id=txn.id,
            event_type=kind,
            source=source,
            review_state="REQUIRES_REVIEW",
            payload=jsonable(
                {
                    "symbol": instrument.symbol if instrument else None,
                    "external_reference": reference,
                    "source_file_id": source_file_id,
                    "thesis_id": metadata.get("thesis_id"),
                    "strategy_id": metadata.get("strategy_id"),
                    "rationale": rationale,
                    "risk_method": "Trade-date close counterfactual, not a pre-execution live risk measurement",
                }
            ),
        )
        self.session.add(event)
        self.session.flush()

        breaches = list(after["breaches"])
        if instrument and kind in {"BUY", "SHORT"} and not metadata.get("thesis_id"):
            breaches.append(
                {
                    "metric": "MISSING_THESIS",
                    "severity": "WARN",
                    "state": "OPEN",
                    "symbol": instrument.symbol,
                }
            )
        if any(Decimal(c["amount"]) < 0 for c in after["cash"]):
            breaches.append({"metric": "NEGATIVE_CASH", "severity": "WARN", "state": "OPEN"})
        self.session.add(
            models.TradeRiskSnapshot(
                trade_id=event.id,
                before=jsonable(trade_risk_snapshot(before)),
                after=jsonable(trade_risk_snapshot(after)),
                breaches=breaches,
            )
        )
        audit(
            self.session,
            "LEDGER_TRANSACTION_CREATED",
            "portfolio_transaction",
            txn.id,
            {
                "portfolio_id": portfolio.id,
                "type": kind,
                "amount": amount,
                "currency": currency,
                "fx": fx,
                "source": source,
                "source_file_id": source_file_id,
                "context": context.model_dump(mode="json"),
            },
            actor,
        )
        self.session.flush()
        payloads = load_entries(self.session, portfolio.id)[1]
        enrich_cash_effects(payloads, entries, state.cash_service.movements)
        return {**next(t for t in payloads if t["id"] == txn.id), "trade_event_id": event.id}


class TradeMonitorService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, portfolio_key: str | None = None) -> list[TradeMonitorRow]:
        portfolio, _ = PortfolioValuationService(self.session).portfolio(portfolio_key)
        transactions = TRANSACTIONS.validate_python(
            transaction_views(self.session, portfolio.id), strict=True
        )
        txns = {t["id"]: t for t in transactions}
        risks = {
            r.trade_id: r
            for r in self.session.scalars(
                select(models.TradeRiskSnapshot)
                .join(models.TradeEvent, models.TradeEvent.id == models.TradeRiskSnapshot.trade_id)
                .where(models.TradeEvent.portfolio_id == portfolio.id)
            ).all()
        }
        rows = self.session.scalars(
            select(models.TradeEvent)
            .where(models.TradeEvent.portfolio_id == portfolio.id)
            .order_by(models.TradeEvent.created_at.desc())
            .limit(500)
        ).all()
        result: list[TradeMonitorRow] = []
        instruments = {r.symbol: r for r in self.session.scalars(select(models.Instrument)).all()}
        marks = MarketPriceResolver(self.session, [r.id for r in instruments.values()])
        now = datetime.now(UTC)
        for row in rows:
            risk = risks.get(row.id)
            txn = txns.get(row.transaction_id)
            if txn is None:
                raise ValueError("Recorded trade has no effective transaction in its portfolio")
            metadata = finite_object(METADATA.validate_python(row.payload, strict=True))
            protected = TradeMonitorRow.__required_keys__ | txn.keys()
            if metadata.keys() & (protected - LEGACY_CONTEXT_FIELDS):
                raise ValueError("Recorded trade metadata conflicts with authoritative evidence")
            source_transaction = finite_object(txn)
            for key in metadata.keys() & txn.keys() & LEGACY_CONTEXT_FIELDS:
                metadata[key] = source_transaction[key]
            symbol = txn.get("symbol")
            instrument = instruments.get(symbol) if symbol is not None else None
            mark = marks.resolve(instrument.id, now) if instrument else None
            sector = instrument.sector if instrument else None
            before = TRADE_RISK.validate_python(risk.before, strict=True) if risk else None
            after = TRADE_RISK.validate_python(risk.after, strict=True) if risk else None
            record = MONITOR_ROW.validate_python(
                {
                    **txn,
                    "id": row.id,
                    "transaction_id": row.transaction_id,
                    "detected_at": row.created_at.isoformat(),
                    "review_state": row.review_state,
                    "pre_beta": before.get("beta") if before else None,
                    "post_beta": after.get("beta") if after else None,
                    "weight_before": position_weight(before, symbol),
                    "weight_after": position_weight(after, symbol),
                    "sector_weight_before": sector_weight(before, sector),
                    "sector_weight_after": sector_weight(after, sector),
                    "risk_as_of": after.get("as_of") if after else None,
                    "current_price": str(mark.value) if mark else None,
                    "current_price_provenance": marks.describe(instrument.id, now)
                    if instrument
                    else None,
                    "breaches": risk.breaches if risk else [],
                    **metadata,
                },
                strict=True,
            )
            result.append(record)
        return result

    def review(
        self, trade_id: str, state: str, note: str, actor: str | None = None
    ) -> TradeReviewReceipt:
        row = self.session.get(models.TradeEvent, trade_id)
        if row is None:
            raise ValueError("Trade not found")
        receipt = REVIEW_RECEIPT.validate_python(
            {"id": trade_id, "state": state, "note": note}, strict=True
        )
        if not receipt["note"].strip():
            raise ValueError("A valid review state and note are required")
        row.review_state = state
        review = models.TradeReview(trade_id=trade_id, actor_user_id=actor, state=state, note=note)
        self.session.add(review)
        audit(
            self.session,
            "TRADE_REVIEWED",
            "trade_event",
            trade_id,
            {"state": state, "note": note},
            actor,
        )
        self.session.commit()
        return receipt


class PortfolioReconciliationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def reconcile(self, portfolio_key: str | None = None) -> ReconciliationResult:
        latest = PortfolioValuationService(self.session).latest(portfolio_key)
        header = HEADER.validate_python(latest, strict=True)
        portfolio_id = header["portfolio"]["id"]
        broker = self.session.scalar(
            select(models.BrokerAccountSnapshot)
            .where(models.BrokerAccountSnapshot.portfolio_id == portfolio_id)
            .order_by(models.BrokerAccountSnapshot.as_of.desc())
            .limit(1)
        )
        if broker is None:
            return {
                "state": "BROKER_NOT_CONNECTED",
                "source": "INTERNAL LEDGER",
                "as_of": header["as_of"],
                "internal_nav": header["portfolio"]["nav"],
                "items": [],
                "warnings": [
                    "No broker snapshot available; reference values are not broker balances"
                ],
            }
        data = BOOK.validate_python(latest, strict=True)
        payload = BROKER.validate_python(broker.payload, strict=True)
        observations: list[ReconciliationItem] = []

        def compare(
            kind: BreakType,
            key: str,
            internal: str | int | float | Decimal | None,
            external: str | int | float | Decimal | None,
            tolerance: Decimal = Decimal(".01"),
        ) -> None:
            # Validate either observed side even when the counterpart is missing.
            if internal is not None:
                decimal(internal)
            if external is not None:
                decimal(external)
            if internal is None or external is None:
                observations.append(
                    {
                        "type": kind,
                        "key": key,
                        "internal": jsonable(internal),
                        "external": jsonable(external),
                        "difference": None,
                        "severity": "WARN",
                    }
                )
            else:
                difference = decimal(internal) - decimal(external)
                if abs(difference) > tolerance:
                    observations.append(
                        {
                            "type": kind,
                            "key": key,
                            "internal": str(internal),
                            "external": str(external),
                            "difference": str(difference),
                            "severity": "WARN",
                        }
                    )

        compare("NAV_MISMATCH", "NAV", data["portfolio"]["nav"], broker.nav)
        internal_cash = {r["currency"]: r["amount"] for r in data["cash"]}
        external_cash = {r["currency"]: r["amount"] for r in payload.get("cash", [])}
        for currency in internal_cash.keys() | external_cash.keys():
            compare(
                "CASH_MISMATCH",
                currency,
                internal_cash.get(currency, "0"),
                external_cash.get(currency, "0"),
            )
        internal_positions = {r["symbol"]: r for r in data["positions"]}
        external_positions = {r["symbol"]: r for r in payload.get("positions", [])}
        for symbol in internal_positions.keys() | external_positions.keys():
            left: PositionAmount = internal_positions.get(symbol, {"symbol": symbol})
            right: PositionAmount = external_positions.get(symbol, {"symbol": symbol})
            compare(
                "QUANTITY_MISMATCH",
                symbol,
                left.get("quantity", "0"),
                right.get("quantity", "0"),
                Decimal(".00000001"),
            )
            compare(
                "COST_BASIS_MISMATCH", symbol, left.get("average_cost"), right.get("average_cost")
            )
        details = self.session.execute(
            select(models.TransactionDetail, models.PortfolioTransaction)
            .join(
                models.PortfolioTransaction,
                models.PortfolioTransaction.id == models.TransactionDetail.transaction_id,
            )
            .where(models.PortfolioTransaction.portfolio_id == portfolio_id)
        ).all()
        effective = {t["id"]: t for t in data["transactions"] if t.get("ledger_state") != "VOID"}
        linked: dict[str, EffectiveTransaction] = {}
        for detail, transaction in details:
            execution_id = detail.metadata_json.get("execution_id")
            if not execution_id or transaction.id not in effective:
                continue
            if not isinstance(execution_id, str):
                raise ValueError("Recorded execution identity must be text")
            linked[execution_id] = effective[transaction.id]
        snapshots = self.session.scalars(
            select(models.BrokerAccountSnapshot)
            .where(models.BrokerAccountSnapshot.portfolio_id == portfolio_id)
            .order_by(models.BrokerAccountSnapshot.as_of)
        ).all()
        fills = {
            f["execution_id"]: f
            for s in snapshots
            if s.payload.get("account_fingerprint") == payload.get("account_fingerprint")
            for f in BROKER.validate_python(s.payload, strict=True).get("fills", [])
        }
        for fill in fills.values():
            pair = linked.get(fill["execution_id"])
            if pair is None:
                observations.append(
                    {
                        "type": "UNMATCHED_BROKER_FILL",
                        "key": fill["execution_id"],
                        "internal": None,
                        "external": jsonable(fill),
                        "difference": None,
                        "severity": "WARN",
                        "snapshot_id": broker.id,
                    }
                )
            else:
                compare(
                    "FILL_QUANTITY_MISMATCH",
                    fill["execution_id"],
                    pair.get("quantity"),
                    fill["quantity"],
                    Decimal(".00000001"),
                )
                compare(
                    "FILL_PRICE_MISMATCH",
                    fill["execution_id"],
                    pair.get("price"),
                    fill["price"],
                    Decimal(".00000001"),
                )
                compare(
                    "COMMISSION_MISMATCH",
                    fill["execution_id"],
                    pair.get("commission"),
                    fill.get("commission"),
                )
        existing = self.session.scalars(
            select(models.PortfolioReconciliationBreak).where(
                models.PortfolioReconciliationBreak.portfolio_id == portfolio_id,
                models.PortfolioReconciliationBreak.state == "OPEN",
            )
        ).all()
        current_keys = {(o["type"], o["key"]) for o in observations}
        for row in existing:
            if (row.break_type, row.payload.get("key")) not in current_keys:
                row.state = "RESOLVED"
                audit(
                    self.session,
                    "RECONCILIATION_BREAK_CLEARED",
                    "reconciliation_break",
                    row.id,
                    {"snapshot_id": broker.id},
                )
        for observation in observations:
            matched = next(
                (
                    r
                    for r in existing
                    if r.break_type == observation["type"]
                    and r.payload.get("key") == observation["key"]
                ),
                None,
            )
            if matched is None:
                matched = models.PortfolioReconciliationBreak(
                    portfolio_id=portfolio_id,
                    external_snapshot_id=broker.id,
                    break_type=observation["type"],
                    severity=observation["severity"],
                    payload=jsonable(observation),
                )
                self.session.add(matched)
                self.session.flush()
            elif matched.payload != observation:
                audit(
                    self.session,
                    "RECONCILIATION_BREAK_UPDATED",
                    "reconciliation_break",
                    matched.id,
                    {"before": matched.payload, "after": observation},
                )
                matched.payload = jsonable(observation)
                matched.external_snapshot_id = broker.id
            observation["id"] = matched.id
        audit(
            self.session,
            "PORTFOLIO_RECONCILED",
            "portfolio",
            portfolio_id,
            {"snapshot_id": broker.id, "breaks": len(observations)},
        )
        self.session.commit()
        return {
            "state": "BREAKS" if observations else "MATCHED",
            "items": observations,
            "source": broker.source,
            "broker_as_of": broker.as_of.isoformat(),
            "internal_as_of": data["as_of"],
            "warnings": [
                "Comparison uses independently timestamped snapshots; timing differences may explain breaks"
            ],
        }
