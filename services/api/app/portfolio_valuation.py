"""Ledger-driven valuation, performance and risk with immutable calculation records."""
from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from . import models
from .portfolio_domain.types import AccountingPolicy
from .portfolio_domain.postings import BalanceAdjustment, CurrencyMark, outstanding_postings, summarize_postings, transaction_postings
from .portfolio_domain.transaction_cash import enrich_cash_effects
from .portfolio_domain.position_pnl import PositionPnlSession
from .portfolio_domain.position_metrics import ExposurePosition, PortfolioPositionService, position_exposures
from .portfolio_exposure import exposure_service
from .transaction_context import context_payload
from .ledger_revisions import apply_revisions
from .portfolio_engine import Entry, LedgerState, ONE, ZERO, daily_performance, money, nav_total
from .portfolio_seed import ensure_main, profile_for
from .price_sources import FxRateResolver, MarketPriceResolver, close_of_day

VERSION = "knk-nav-4.8"
METHOD = "Policy-selected cost basis; trade-date recognition and settlement cash; recorded transaction FX; beginning-of-day external flows; chain-linked daily returns"


def jsonable(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    return value


def number(value):
    return float(value) if value is not None and math.isfinite(float(value)) else None


def load_entries(session: Session, portfolio_id: str) -> tuple[list[Entry], list[dict[str, Any]]]:
    rows = session.execute(select(models.PortfolioTransaction, models.TransactionDetail).outerjoin(models.TransactionDetail, models.TransactionDetail.transaction_id == models.PortfolioTransaction.id).where(models.PortfolioTransaction.portfolio_id == portfolio_id).order_by(models.PortfolioTransaction.trade_date, models.PortfolioTransaction.created_at, models.PortfolioTransaction.id)).all()
    entries, payloads = [], []
    creators: dict[str, str | None] = {}
    creation_logs = session.execute(select(models.AuditLog.resource_id, models.AuditLog.actor_user_id)
        .join(models.PortfolioTransaction, models.PortfolioTransaction.id == models.AuditLog.resource_id)
        .where(models.PortfolioTransaction.portfolio_id == portfolio_id,
               models.AuditLog.resource_type == "portfolio_transaction",
               models.AuditLog.action == "LEDGER_TRANSACTION_CREATED")
        .order_by(models.AuditLog.created_at, models.AuditLog.id)).all()
    for identifier, actor in creation_logs:
        creators.setdefault(identifier, actor)
    instruments = {r.id: r for r in session.scalars(select(models.Instrument)).all()}
    for txn, detail in rows:
        amount = detail.gross_amount if detail else txn.quantity * txn.price
        if not detail and txn.transaction_type == "DEPOSIT" and not amount:
            raise ValueError("Legacy implicit contribution requires explicit ledger migration")
        entries.append(Entry(
            id=txn.id, day=txn.trade_date, kind=txn.transaction_type, currency=txn.currency,
            quantity=txn.quantity, price=txn.price, fx=txn.fx_rate_to_base, amount=amount,
            fee=txn.fee, commission=detail.commission if detail else ZERO,
            tax=detail.tax if detail else ZERO, instrument_id=txn.instrument_id,
            multiplier=detail.contract_multiplier if detail else ONE, metadata=detail.metadata_json if detail else {},
            settle_date=txn.settle_date, account_id=txn.account_id,
        ))
        instrument = instruments.get(txn.instrument_id)
        payloads.append(jsonable({
            "id": txn.id, "portfolio_id": portfolio_id, "account_id": txn.account_id,
            "type": txn.transaction_type, "transaction_type": txn.transaction_type,
            "symbol": instrument.symbol if instrument else None, "instrument_id": txn.instrument_id,
            "trade_date": txn.trade_date, "settle_date": txn.settle_date,
            "quantity": txn.quantity, "price": txn.price, "gross_amount": amount,
            "currency": txn.currency, "fx_rate_to_base": txn.fx_rate_to_base,
            "base_value": amount * txn.fx_rate_to_base, "fee": txn.fee,
            "commission": detail.commission if detail else ZERO, "tax": detail.tax if detail else ZERO,
            "source": txn.source, "quality": txn.quality, "notes": txn.notes,
            "created_at": txn.created_at, "updated_at": txn.updated_at,
            "source_file_id": detail.source_file_id if detail else None,
            "external_key": detail.external_key if detail else None,
            **context_payload(detail.metadata_json if detail else {}, creators.get(txn.id)),
            "reconciliation_state": detail.reconciliation_state if detail else "INTERNAL_ONLY",
            "metadata": detail.metadata_json if detail else {},
        }))
    return apply_revisions(session, portfolio_id, entries, payloads)


def metric_summary(curve, cash_flows, end, risk_free=0):
    from .performance_domain.contracts import FeeBasis, Frequency, PerformanceSettings, ReturnObservation
    from .performance_domain.drawdowns import drawdowns
    from .performance_domain.metrics import measured, period_returns, sample_statistics
    from .performance_domain.money_weighted import money_weighted
    from .performance_domain.series import periods

    def value(row, exact, legacy):
        item = row.get(exact, row.get(legacy))
        return Decimal(str(item)) if item is not None else None

    rows = [ReturnObservation(
        date.fromisoformat(row["date"]), value(row, "net_return_exact", "return"),
        value(row, "opening_nav_exact", "opening_nav"), value(row, "nav_exact", "equity"),
        value(row, "external_flow_exact", "external_flow"), value(row, "pnl_exact", "daily_pnl"),
        value(row, "fee_expense_exact", "fee_expense_exact"),
        value(row, "benchmark_return_exact", "benchmark_return"), row["quality"],
    ) for row in curve]
    settings = PerformanceSettings(risk_free_rate=Decimal(str(risk_free)))
    daily = periods(rows, Frequency.DAILY, FeeBasis.NET)
    metrics = {**period_returns(rows, settings), **sample_statistics(daily, rows, settings),
               **money_weighted(rows, None, FeeBasis.NET)}
    dd = drawdowns(daily)
    metrics["max_drawdown"] = measured(dd["maximum"], len(rows))
    metrics["current_drawdown"] = measured(dd["current"], len(rows))
    cagr = metrics["cagr"].value
    metrics["calmar"] = measured(float(cagr) / abs(float(dd["maximum"])) if cagr is not None and dd["maximum"] else None, len(rows), "RATIO")
    result = {key: number(metric.value) for key, metric in metrics.items()}
    volatility = result["volatility"]
    result["daily_volatility"] = volatility / math.sqrt(252) if volatility is not None else None
    result["observations"] = sum(row.day.weekday() < 5 for row in rows)
    result["calendar_days"] = (end - rows[0].day).days if rows else 0
    result["metric_states"] = {key: {"state": metric.state, "reason": metric.reason, "observations": metric.observations} for key, metric in metrics.items()}
    warnings = list(dict.fromkeys(f"{metric.state}: {metric.reason}" for metric in metrics.values() if metric.reason))
    return result, warnings

class PortfolioValuationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def portfolio(self, key: str | None = None) -> tuple[models.Portfolio, models.PortfolioProfile]:
        profile = profile_for(self.session, key)
        if profile is None and key is None:
            ensure_main(self.session)
            profile = profile_for(self.session)
        if profile is None:
            raise ValueError("Portfolio is not enabled for the audited ledger")
        portfolio = self.session.get(models.Portfolio, profile.portfolio_id)
        if portfolio is None:
            raise ValueError("Portfolio record is unavailable")
        return portfolio, profile

    def fingerprint(self, portfolio_id, end):
        now = datetime.now(timezone.utc)
        freshness_epoch = now.strftime("%Y-%m-%dT%H:%M") if end >= now.date() else "HISTORICAL"
        parts = [VERSION, portfolio_id, end.isoformat(), freshness_epoch]
        for model in (models.PortfolioTransaction, models.TransactionDetail, models.TransactionRevision, models.MarketObservation, models.FxObservation, models.SourcePrecedenceRule, models.PortfolioProfile, models.PortfolioBalanceAdjustment, models.RiskLimit):
            query = select(func.count(model.id), func.max(model.updated_at))
            if hasattr(model, "portfolio_id"):
                query = query.where(model.portfolio_id == portfolio_id)
            parts.append(str(self.session.execute(query).one()))
        return hashlib.sha256("|".join(parts).encode()).hexdigest()

    def latest(self, key: str | None = None, *, force: bool = False, end: date | None = None, commit: bool = True) -> dict[str, Any]:
        portfolio, _ = self.portfolio(key)
        day = end or datetime.now(timezone.utc).date()
        fingerprint = self.fingerprint(portfolio.id, day)
        if not force:
            cached = self.session.scalar(select(models.PortfolioValuationRun).where(models.PortfolioValuationRun.portfolio_id == portfolio.id, models.PortfolioValuationRun.fingerprint == fingerprint).order_by(models.PortfolioValuationRun.created_at.desc()).limit(1))
            if cached:
                return cached.payload
        payload = self.calculate(portfolio.id, day)
        run = models.PortfolioValuationRun(
            portfolio_id=portfolio.id, fingerprint=fingerprint, valuation_date=day,
            status="SUCCEEDED" if payload["portfolio"]["nav"] is not None else "INCOMPLETE",
            nav=Decimal(payload["portfolio"]["nav"]) if payload["portfolio"]["nav"] is not None else None,
            payload={},
        )
        self.session.add(run)
        self.session.flush()
        payload["valuation_run_id"] = run.id
        run.payload = payload
        from .lot_persistence import persist_lots
        persist_lots(self.session, run.id, payload["lots"], payload["lot_matches"])
        from .accounting_persistence import persist_accounting
        persist_accounting(self.session, portfolio.id, run.id, payload["accounting"]["items"])
        for row in payload["positions"]:
            self.session.add(models.PositionValuation(
                valuation_run_id=run.id, instrument_id=row["instrument_id"],
                quantity=Decimal(row["quantity"]),
                price=Decimal(row["market_price"]) if row["market_price"] is not None else None,
                fx_rate=Decimal(row["fx_rate"]) if row["fx_rate"] is not None else None,
                market_value=Decimal(row["market_value"]) if row["market_value"] is not None else None,
                provenance={"price": row["price_provenance"], "fx": row["fx_provenance"]},
            ))
        if run.nav is not None:
            p = payload["portfolio"]
            self.session.add(models.NavSnapshot(portfolio_id=portfolio.id, as_of=datetime.now(timezone.utc), nav=run.nav, cash=Decimal(p["cash"]), market_value=Decimal(p["market_value"]), quality=payload["quality"]))
            self.session.execute(delete(models.PortfolioPosition).where(models.PortfolioPosition.portfolio_id == portfolio.id))
            self.session.execute(delete(models.PortfolioCashBalance).where(models.PortfolioCashBalance.portfolio_id == portfolio.id))
            for row in payload["positions"]:
                self.session.add(models.PortfolioPosition(portfolio_id=portfolio.id, instrument_id=row["instrument_id"], quantity=Decimal(row["quantity"]), average_cost=Decimal(row["average_cost"]), market_price=Decimal(row["market_price"]), market_value=Decimal(row["market_value"]), unrealised_pnl=Decimal(row["unrealised_pnl"]), realised_pnl=Decimal(row["realised_pnl"]), weight=Decimal(row["weight"]), as_of=datetime.fromisoformat(row["as_of"]), quality=payload["quality"]))
            for row in payload["cash"]:
                self.session.add(models.PortfolioCashBalance(portfolio_id=portfolio.id, currency=row["currency"], amount=Decimal(row["amount"]), quality=payload["quality"]))
            self.session.execute(delete(models.DailyReturn).where(models.DailyReturn.portfolio_id == portfolio.id))
            for row in payload["curve"]:
                if row["return"] is not None:
                    self.session.add(models.DailyReturn(portfolio_id=portfolio.id, date=date.fromisoformat(row["date"]), return_value=Decimal(str(row["return"]))))
        if commit:
            self.session.commit()
        else:
            self.session.flush()
        return payload

    def calculate(self, key=None, end=None):
        portfolio, profile = self.portfolio(key)
        end = end or datetime.now(timezone.utc).date()
        now = datetime.now(timezone.utc)
        entries, transactions = load_entries(self.session, portfolio.id)
        entries = [r for r in entries if r.day <= end]
        if not entries:
            raise ValueError("Portfolio has no transactions at this date")
        start = min(r.day for r in entries)
        instruments = {r.id: r for r in self.session.scalars(select(models.Instrument)).all()}
        benchmark = next((r for r in instruments.values() if r.symbol == profile.configuration.get("benchmark", "SPY")), None)
        ids = {r.instrument_id for r in entries if r.instrument_id}
        ids.update(r.metadata["child_instrument_id"] for r in entries if r.metadata.get("child_instrument_id"))
        if benchmark:
            ids.add(benchmark.id)
        prices = MarketPriceResolver(self.session, ids, start)
        fx = FxRateResolver(self.session)
        if profile.configuration.get("price_mode") == "DEMO_ONLY":
            prices.rules = {}
            for key in list(prices.grouped):
                prices.grouped[key] = {group: value for group, value in prices.grouped[key].items() if group[0] == "DEMO"}
            for pair in list(fx.groups):
                fx.groups[pair] = {group: value for group, value in fx.groups[pair].items() if group[0] == "DEMO"}
        adjustments = self.session.scalars(select(models.PortfolioBalanceAdjustment).where(models.PortfolioBalanceAdjustment.portfolio_id == portfolio.id)).all()
        days = {r.day for r in entries} | {r.settlement for r in entries} | {end}
        days.update(row.effective_date for row in adjustments)
        for values in prices.series.values():
            days.update(r.timestamp.date() for r in values if start <= r.timestamp.date() <= end)
        days = sorted(d for d in days if start <= d <= end)
        state = LedgerState(policy=AccountingPolicy.from_config(profile.configuration))
        index, previous_nav, return_index, peak, previous_benchmark, benchmark_equity = 0, ZERO, ONE, ONE, None, ZERO
        previous_accrued_fees = ZERO
        curve, histories, last_positions, last_cash, warnings = [], defaultdict(dict), [], [], []
        previous_position_values = {}
        last_daily_contributions = {}
        for day in days:
            at = min(close_of_day(day), now) if day == now.date() else close_of_day(day)
            flow_before = state.external_flows
            fees_before = state.fees
            daily_attribution = PositionPnlSession(
                {key: lot.quantity for key, lot in state.lots.items()}, previous_position_values,
            )
            movement_start = len(state.cash_service.movements)
            while index < len(entries) and entries[index].day <= day:
                state.apply(entries[index])
                daily_attribution.record(entries[index])
                index += 1
            state.advance(day)
            flows = state.external_flows - flow_before
            position_values, position_rows, cash_rows, missing = {}, [], [], []
            total_cash = ZERO
            settled_cash_components = []
            settled_cash = available_cash = settlement_receivables = settlement_payables = ZERO
            sources = []
            for currency, cash_balance in state.cash_service.balances(day).items():
                amount = cash_balance.economic
                if amount == 0 and cash_balance.settled == 0 and cash_balance.receivable == 0 and cash_balance.payable == 0:
                    continue
                rate, provenance = fx.resolve(currency, portfolio.base_currency, at)
                value = amount * rate if rate is not None else None
                cash_rows.append({"currency": currency, "amount": amount, "settled": cash_balance.settled, "receivable": cash_balance.receivable, "payable": cash_balance.payable, "available": cash_balance.available, "base_value": money(value) if value is not None else None, "base_value_exact": value, "as_of": provenance["as_of"], "quality": provenance["data_state"], "fx_rate": rate, "fx_provenance": provenance, "source": provenance["source"]})
                sources.append(provenance)
                if value is None:
                    missing.append(f"Missing FX {currency}/{portfolio.base_currency}")
                else:
                    total_cash += value
                    settled_cash += cash_balance.settled * rate
                    settled_cash_components.append(cash_balance.settled * rate)
                    available_cash += cash_balance.available * rate
                    settlement_receivables += cash_balance.receivable * rate
                    settlement_payables += cash_balance.payable * rate
            for instrument_id, lot in state.lots.items():
                if lot.quantity == 0:
                    continue
                item = instruments[instrument_id]
                price = prices.resolve(instrument_id, at)
                provenance = prices.describe(instrument_id, at)
                rate, fx_provenance = fx.resolve(item.currency, portfolio.base_currency, at)
                measurement = PortfolioPositionService.measure(lot, price.value if price else None, rate)
                value = measurement.base_value
                if value is None:
                    missing.append(f"{item.symbol}: missing {'price' if not price else 'FX'}")
                else:
                    position_values[instrument_id] = value
                sources.extend([provenance, fx_provenance])
                position_rows.append({
                    "id": instrument_id, "instrument_id": instrument_id, "symbol": item.symbol, "name": item.name,
                    **measurement.payload(),
                    "currency": item.currency, "sector": item.sector or "Unclassified", "country": item.country, "industry": item.industry or "Unclassified",
                    "asset_class": item.asset_class, "contract_multiplier": lot.multiplier,
                    "source": provenance["source"], "quality": provenance["data_state"], "as_of": provenance["as_of"],
                    "price_provenance": provenance, "fx_provenance": fx_provenance, "fx_rate": rate,
                    "weight": ZERO, "beta": None, "risk_contribution": None,
                })
            balances = defaultdict(Decimal)
            native_balances = defaultdict(Decimal)
            for adjustment in adjustments:
                if adjustment.effective_date <= day:
                    native_balances[(adjustment.bucket, adjustment.currency)] += adjustment.amount
            balance_exposure_rows = []
            for (bucket, currency), amount in sorted(native_balances.items()):
                if not amount:
                    continue
                rate, adjustment_provenance = fx.resolve(currency, portfolio.base_currency, at)
                sources.append(adjustment_provenance)
                value = amount * rate if rate is not None else None
                sign = ONE if bucket in {"accrued_income", "receivables"} else -ONE
                balance_exposure_rows.append({"bucket": bucket, "currency": currency, "amount": amount,
                                              "base_value": value * sign if value is not None else None,
                                              "fx_rate": rate, "fx_provenance": adjustment_provenance})
                if value is None:
                    missing.append(f"Missing adjustment FX {currency}")
                else:
                    balances[bucket] += value
            balances["receivables"] += settlement_receivables
            balances["payables"] += settlement_payables
            totals = nav_total(settled_cash, list(position_values.values()), dict(balances), cash_components=settled_cash_components)
            nav = None if missing else totals["nav"]
            daily_pnl, daily_return = (None, None) if nav is None or previous_nav is None else daily_performance(previous_nav, nav, flows)
            if daily_return is not None and return_index is not None:
                return_index *= 1 + daily_return
                peak = max(peak, return_index)
            else:
                return_index = None
            dd = float(return_index / peak - 1) if peak and return_index is not None else None
            benchmark_price = prices.resolve(benchmark.id, at) if benchmark else None
            benchmark_fx, _ = fx.resolve(benchmark.currency, portfolio.base_currency, at) if benchmark else (None, {})
            benchmark_base = benchmark_price.value * benchmark_fx if benchmark_price and benchmark_fx else None
            benchmark_return = (benchmark_base / previous_benchmark - 1 if previous_benchmark else ZERO if not curve else None) if benchmark_base else None
            benchmark_equity = (benchmark_equity + flows) * (1 + benchmark_return) if benchmark_equity is not None and benchmark_return is not None else None
            previous_benchmark = benchmark_base
            marked_values = {key: position_values.get(key) for key, lot in state.lots.items() if lot.quantity}
            daily_details = daily_attribution.finish(marked_values, state.cash_service.movements[movement_start:])
            daily_contributions = {key: detail.pnl for key, detail in daily_details.items()}
            for row in position_rows:
                row["weight"] = position_values[row["instrument_id"]] / nav if nav and row["market_value"] is not None else ZERO
                row["daily_pnl"] = number(daily_contributions.get(row["instrument_id"], ZERO)) if nav is not None and previous_nav is not None else None
                row["daily_pnl_details"] = daily_details[row["instrument_id"]].payload()
                row["return"] = number(row["return"])
            for instrument_id in ids:
                observation = prices.resolve(instrument_id, at)
                item = instruments[instrument_id]
                rate, _ = fx.resolve(item.currency, portfolio.base_currency, at)
                if observation and rate is not None:
                    histories[instrument_id][day] = float(observation.value * rate)
            curve.append({
                "date": day.isoformat(), "equity": number(money(nav)) if nav is not None else None,
                "opening_nav": number(money(previous_nav)) if previous_nav is not None else None,
                "daily_pnl": number(money(daily_pnl)) if daily_pnl is not None else None,
                "external_flow": number(money(flows)), "return": number(daily_return),
                "nav_exact": nav, "opening_nav_exact": previous_nav,
                "pnl_exact": daily_pnl, "external_flow_exact": flows,
                "net_return_exact": daily_return,
                "fee_expense_exact": state.fees - fees_before + balances["accrued_fees"] - previous_accrued_fees if not missing else None,
                "benchmark": number(money(benchmark_equity)) if benchmark_equity is not None else None,
                "benchmark_return": number(benchmark_return), "benchmark_return_exact": benchmark_return,
                "drawdown": dd, "return_index": number(return_index),
                "quality": "UNAVAILABLE" if missing else ("STALE" if any(p.get("stale") for p in sources) else "CALCULATED"),
            })
            previous_nav = nav
            previous_accrued_fees = balances["accrued_fees"]
            previous_position_values = marked_values
            last_positions, last_cash, last_daily_contributions = position_rows, cash_rows, daily_contributions
            if day == end:
                warnings.extend(missing)
                selected_sources = sources
                final_totals = totals

        performance, performance_warnings = metric_summary(curve, state.flow_events, end, float(profile.configuration.get("risk_free_rate", 0)))
        warnings.extend(performance_warnings)
        risk, correlations = self.risk(histories, last_positions, benchmark.id if benchmark else None, nav, performance, profile.configuration.get("risk_settings"))
        risk_model = correlations.pop("model")
        if risk_model["state"] != "AVAILABLE":
            warnings.append("Risk: " + risk_model["reason"])
        position_weights = position_exposures([
            ExposurePosition(row["instrument_id"], row["sector"], position_values.get(row["instrument_id"]),
                             Decimal(str(row["beta"])) if row["beta"] is not None else None)
            for row in last_positions
        ], nav)
        for row in last_positions:
            row.update(position_weights[row["instrument_id"]])
        marked_exposure = exposure_service(last_positions, last_cash, balance_exposure_rows, nav)
        exposure = marked_exposure.groups()
        risk.update({
            "max_position_weight": max((abs(float(p["weight"])) for p in last_positions), default=0),
            "top_five_concentration": sum(sorted((abs(float(p["weight"])) for p in last_positions), reverse=True)[:5]),
            "max_sector_weight": number(max((abs(r["weight"]) for r in exposure["sector"]), default=ZERO)) if nav and all(r["weight"] is not None for r in exposure["sector"]) else None,
            "max_currency_weight": number(max((abs(r["weight"]) for r in exposure["currency"]), default=ZERO)) if nav and all(r["weight"] is not None for r in exposure["currency"]) else None,
            "max_country_weight": number(max((abs(r["weight"]) for r in exposure["country"]), default=ZERO)) if nav and all(r["weight"] is not None for r in exposure["country"]) else None,
            "max_industry_weight": number(max((abs(r["weight"]) for r in exposure["industry"]), default=ZERO)) if nav and all(r["weight"] is not None for r in exposure["industry"]) else None,
            "stale_exposure": number(marked_exposure.freshness()["stale_nav_pct"]),
            "cash_weight": float(total_cash / nav) if nav else None,
        })
        for metric, source in (("var_loss_95", "var_95"), ("cvar_loss_95", "cvar_95"), ("drawdown_loss", "current_drawdown")):
            risk[metric] = abs(risk[source]) if risk.get(source) is not None else None
        if nav is None:
            risk = {key: value if key == "observations" else None for key, value in risk.items()}
            for row in last_positions:
                row["weight"] = None
            for rows in exposure.values():
                for row in rows:
                    row["weight"] = None
        limits = self.session.execute(select(models.RiskLimit, models.RiskPolicy).join(models.RiskPolicy, models.RiskPolicy.id == models.RiskLimit.policy_id).where(models.RiskPolicy.portfolio_id == portfolio.id, models.RiskPolicy.enabled.is_(True))).all()
        breaches = []
        for limit, _ in limits:
            if limit.id in profile.configuration.get("disabled_risk_limit_ids", []):
                continue
            actual = risk.get(limit.metric)
            if actual is not None and (actual > float(limit.threshold) if limit.direction == "MAX" else actual < float(limit.threshold)):
                breaches.append({"limit_id": limit.id, "metric": limit.metric, "value": actual, "threshold": str(limit.threshold), "severity": "WARN", "state": "OPEN", "as_of": now.isoformat()})
        if any(p.get("stale") for p in selected_sources):
            warnings.append("CALCULATED WITH STALE DATA: selected prices/FX are retained; no demo substitution")
            warnings.append("Risk estimates include carried-forward stale observations and may understate variability")
        if any(p.get("conflict") for p in selected_sources):
            warnings.append("Material same-date source differences exceed 1%; review price provenance")
        if any(p["amount"] < 0 for p in last_cash):
            warnings.append("Negative native-currency cash: review funding or FX conversion")
        if any(row["beta"] is None for row in last_positions):
            warnings.append("Some position risk metrics have insufficient paired price history")
        warnings.append("Risk uses current security weights; cash FX and liability sensitivities are excluded. Historical valuations use currently accepted source versions, not point-in-time research snapshots.")
        categories = {p.get("source_category") for p in selected_sources} - {None}
        quality = "UNAVAILABLE" if nav is None else ("CALCULATED WITH STALE DATA" if any(p.get("stale") for p in selected_sources) else "CALCULATED" if not categories else "DEMO DATA" if categories <= {"DEMO"} else "FILE IMPORT" if categories <= {"FILE"} else "MIXED SOURCES")
        market_sources = sorted({p["source"] for p in selected_sources if p.get("source") != "IDENTITY"})
        source_name = "INTERNAL LEDGER" + (" / " + ", ".join(market_sources) if market_sources else "")
        market_stamps = [p["as_of"] for p in selected_sources if p.get("as_of") and p.get("source") != "IDENTITY"]
        as_of = min(market_stamps) if market_stamps else now.isoformat()
        investment = sum((lot.realised for lot in state.lots.values()), ZERO) + sum((position_values.get(key, ZERO) - lot.cost_base for key, lot in state.lots.items()), ZERO)
        cash_fx = total_cash - state.cash_book_base
        balance_effect = final_totals["nav"] - total_cash - final_totals["market_value"]
        total_pnl = nav - state.external_flows if nav is not None else None
        expected = state.external_flows + investment + state.income - state.expensed_fees - state.taxes + cash_fx + state.adjustments + balance_effect
        difference = money(nav - expected) if nav is not None else None
        if difference and abs(difference) > Decimal(".01"):
            warnings.append("NAV RECONCILIATION FAILED: accounting components do not balance")
        attribution = []
        for key, lot in state.lots.items():
            item = instruments[key]
            unrealised = position_values.get(key, ZERO) - lot.cost_base if key in position_values or lot.quantity == 0 else None
            contribution = lot.realised + unrealised + lot.income - lot.expensed_charges if unrealised is not None else None
            daily_value = last_daily_contributions.get(key, ZERO)
            attribution.append({"symbol": item.symbol, "sector": item.sector, "currency": item.currency, "realised": money(lot.realised), "unrealised": money(unrealised) if unrealised is not None else None, "income": money(lot.income), "fees": money(lot.charges), "daily_pnl": money(daily_value) if nav is not None and daily_value is not None else None, "daily_pnl_details": daily_details[key].payload() if key in daily_details else None, "total_pnl": money(contribution) if contribution is not None else None, "contribution": number(contribution / portfolio.reference_capital) if contribution is not None else None})
        states = performance.pop("metric_states")
        metric_metadata = {key: {"value": value, "portfolio": profile.code, "base_currency": portfolio.base_currency, "start": start.isoformat(), "end": end.isoformat(), "benchmark": profile.configuration.get("benchmark", "SPY"), "methodology": METHOD, "source": source_name, "calculated_at": now.isoformat(), "quality": quality, **states.get(key, {"state": "AVAILABLE" if value is not None else "INSUFFICIENT_DATA"})} for key, value in {**performance, **risk}.items()}
        balance_sheet_difference = money(final_totals["gross_asset_value"] - final_totals["liabilities"] - nav, 8) if nav is not None else None
        if balance_sheet_difference:
            warnings.append("NAV BALANCE SHEET BREAK: assets less liabilities do not equal NAV")
        p = {
            "id": portfolio.id, "code": profile.code, "name": portfolio.name, "base_currency": portfolio.base_currency,
            "reference_capital": portfolio.reference_capital, "opening_capital": portfolio.reference_capital,
            **({k: money(v) if isinstance(v, Decimal) else v for k, v in final_totals.items()} if nav is not None else dict.fromkeys(final_totals)),
            "nav": money(nav) if nav is not None else None, "total_pnl": money(total_pnl) if total_pnl is not None else None,
            "cash": money(total_cash) if all(c["base_value"] is not None for c in last_cash) else None,
            "market_value": money(final_totals["market_value"]) if all(p["market_value"] is not None for p in last_positions) else None,
            "gross_asset_value": money(final_totals["gross_asset_value"]) if nav is not None else None,
            "total_return": number(total_pnl / portfolio.reference_capital) if total_pnl is not None else None,
            "cash_weight": number(total_cash / nav) if nav else None,
            "invested_weight": number(final_totals["market_value"] / nav) if nav else None,
            "daily_pnl": curve[-1]["daily_pnl"], "opening_nav": curve[-1]["opening_nav"],
            "quality": quality, "as_of": as_of, "calculated_at": now.isoformat(),
            "view": "INTERNAL LEDGER", "execution_mode": "MANUAL", "broker_mode": "PAPER",
            "price_mode": profile.configuration.get("price_mode", "AUTO"),
            "accounting_policy": state.policy.to_dict(),
            "settled_cash": money(settled_cash) if all(c["base_value"] is not None for c in last_cash) else None,
            "available_cash": money(available_cash) if all(c["base_value"] is not None for c in last_cash) else None,
            "settlement_receivables": money(settlement_receivables) if nav is not None else None,
            "settlement_payables": money(settlement_payables) if nav is not None else None,
        }
        metric_metadata.update({key: {"value": p[key], "portfolio": profile.code, "base_currency": portfolio.base_currency, "source": source_name, "as_of": as_of, "calculated_at": now.isoformat(), "quality": quality, "methodology": METHOD} for key in ("opening_capital", "nav", "cash", "market_value", "total_pnl", "daily_pnl", "cash_weight", "invested_weight")})
        monthly = []
        for month in sorted({p["date"][:7] for p in curve}):
            values = [p["return"] for p in curve if p["date"][:7] == month]
            monthly.append({"month": month, "return": float(np.prod(1 + np.array(values)) - 1) if all(v is not None for v in values) else None})
        postings = [posting for entry in entries for posting in transaction_postings(entry, state.policy)]
        marks = {currency: CurrencyMark(*fx.resolve(currency, portfolio.base_currency, at))
                 for currency in {row.currency for row in adjustments} | set(state.cash)}
        postings.extend(outstanding_postings(
            state.cash_service.movements,
            [BalanceAdjustment(row.id, row.effective_date, row.bucket, row.currency, row.amount, row.reason)
             for row in adjustments], end, marks,
        ))
        posting_totals = summarize_postings(postings)
        enrich_cash_effects(transactions, entries, state.cash_service.movements)
        posting_differences = {name: money(posting_totals[name] - expected_value)
                              for name, expected_value in {
                                  "external_flows": state.external_flows, "income": state.income,
                                  "fees_paid": state.fees, "taxes": state.taxes,
                                  "capitalized_charges": state.capitalized_charges,
                                  "expensed_fees": state.expensed_fees,
                              }.items()}
        if any(posting_differences.values()):
            warnings.append("ACCOUNTING SUBLEDGER BREAK: transaction components differ from replay totals")
        return jsonable({
            "portfolio": p, "positions": last_positions, "cash": last_cash, "transactions": transactions,
            "balance_sheet": {
                "items": final_totals if nav is not None else dict.fromkeys(final_totals),
                "state": "AVAILABLE" if nav is not None else "INCOMPLETE",
                "difference": balance_sheet_difference,
                "reconciliation_state": "INCOMPLETE" if balance_sheet_difference is None else "BREAK" if balance_sheet_difference else "BALANCED",
                "methodology": "Gross assets = positive settled cash by currency + long positions + accrued income + receivables; total liabilities = cash overdrafts + short positions + payables + accrued fees + other liabilities; NAV = gross assets - total liabilities. Settlement balances are included once; book values are not broker-reported.",
                "warnings": list(dict.fromkeys(missing)),
            },
            "cost_basis": {"method": state.policy.method.value, "capitalized_charges": state.capitalized_charges, "expensed_fees": state.expensed_fees},
            "lots": [asdict(lot) for lots in state.cost_basis.open_lots.values() for lot in lots],
            "lot_matches": [asdict(match) for match in state.cost_basis.matches],
            "accounting": {"items": [row.payload() for row in postings], "totals": posting_totals,
                           "reconciliation": {"state": "BREAK" if any(posting_differences.values()) else "BALANCED",
                                              "differences": posting_differences}},
            "performance": performance, "risk": risk, "risk_model": risk_model, "curve": curve, "monthly": monthly, "correlation": correlations,
            "exposures": exposure, "attribution": attribution, "breaches": breaches,
            "exposure_balances": balance_exposure_rows,
            "exposure_methodology": "Signed marked positions, economic cash and net outstanding manual balance buckets; sector and country exclude cash and balance buckets; currency and asset class include them; settlement receivables/payables already included in economic cash",
            "source": source_name, "quality": quality, "as_of": as_of, "calculated_at": now.isoformat(),
            "methodology": METHOD, "calculation_version": VERSION, "metric_metadata": metric_metadata,
            "warnings": list(dict.fromkeys(warnings)), "freshness": marked_exposure.freshness(),
            "reconciliation": {"opening_capital": portfolio.reference_capital, "net_external_flows": money(state.external_flows), "additional_capital_flows": money(state.external_flows - portfolio.reference_capital), "investment_pnl": money(investment) if nav is not None else None, "income": money(state.income), "fees": money(state.fees), "taxes": money(state.taxes), "cash_fx_pnl": money(cash_fx) if nav is not None else None, "adjustments": money(state.adjustments + balance_effect), "expected_nav": money(expected) if nav is not None else None, "difference": difference, "state": "BALANCED" if difference == ZERO else "INCOMPLETE" if difference is None else "BREAK"},
        })

    @staticmethod
    def risk(histories, positions, benchmark_id, nav, performance, settings=None):
        from .risk_statistics import RiskSettings, calculate_risk
        frame = pd.DataFrame(histories).sort_index()
        ordered = sorted(positions, key=lambda row: row["symbol"])
        weights = pd.Series({row["instrument_id"]: float(row["weight"]) for row in ordered}, dtype=float)
        result = calculate_risk(frame, weights, float(nav) if nav is not None else None, benchmark_id,
                                RiskSettings.model_validate(settings or {}))
        for row in positions:
            row.update(result.positions.get(row["instrument_id"], {}))
        risk = {**result.metrics, "max_drawdown": performance.get("max_drawdown"),
                "current_drawdown": performance.get("current_drawdown")}
        evidence = {**result.evidence, "symbols": [row["symbol"] for row in ordered]}
        return risk, {"symbols": evidence["symbols"], "values": evidence["values"], "model": evidence}
