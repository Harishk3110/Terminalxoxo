"""Hypothetical internal hedge sizing. No broker action or ledger mutation."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from . import models
from .portfolio_operations import audit
from .portfolio_valuation import PortfolioValuationService
from .price_sources import FxRateResolver, MarketPriceResolver, close_of_day
from .risk_statistics import RiskSettings, calculate_risk

WARNING = "MANUAL REVIEW REQUIRED - NO ORDER WILL BE SUBMITTED"


class HedgeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    mode: Literal["BETA", "NET", "SECTOR", "CURRENCY"] = "BETA"
    instrument_type: Literal["ETF", "FUTURE_ESTIMATE", "FX_CONVERSION"] = "ETF"
    symbol: str = Field(default="SPY", min_length=1, max_length=30, pattern=r"^[A-Z0-9.\-]+$")
    target: float = Field(default=0.8, ge=-3, le=3, allow_inf_nan=False)
    sector: str = Field(default="Technology", min_length=1, max_length=80)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    fee_bps: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)
    slippage_bps: float = Field(default=0, ge=0, le=500, allow_inf_nan=False)
    assumed_price: float | None = Field(default=None, gt=0, le=1e9, allow_inf_nan=False)
    assumed_beta: float | None = Field(default=None, ge=-5, le=5, allow_inf_nan=False)
    contract_multiplier: float | None = Field(default=None, gt=0, le=1e6, allow_inf_nan=False)


def size_hedge(data: dict, request: HedgeRequest, hedge: dict) -> dict:
    nav = float(data["portfolio"]["nav"] or 0)
    if not math.isfinite(nav) or nav <= 0 or data.get("account_source") == "BROKER":
        raise ValueError("A complete positive internal NAV is required")
    risk, beta = data["risk"], data["risk"].get("beta")
    price, fx, multiplier = (float(hedge[key]) for key in ("price", "fx", "multiplier"))
    if not all(math.isfinite(v) and v > 0 for v in (price, fx, multiplier)):
        raise ValueError("Positive hedge price, FX and multiplier required")
    hbeta = hedge.get("beta")
    is_currency = request.mode == "CURRENCY"
    if is_currency != (request.instrument_type == "FX_CONVERSION"):
        raise ValueError("Currency mode requires an FX conversion estimate")
    if request.mode == "BETA":
        if beta is None or hbeta is None or abs(hbeta) < 1e-6:
            raise ValueError("Sufficient portfolio and nonzero hedge beta history required")
        requested = (
            (Decimal(str(request.target)) - Decimal(str(beta)))
            * Decimal(str(nav))
            / Decimal(str(hbeta))
        )
    elif request.mode == "NET":
        if risk.get("net_exposure") is None:
            raise ValueError("Net exposure is unavailable")
        requested = (Decimal(str(request.target)) - Decimal(str(risk["net_exposure"]))) * Decimal(
            str(nav)
        )
    else:
        dimension, key = (
            ("currency", request.currency) if is_currency else ("sector", request.sector)
        )
        if not is_currency and hedge.get("sector") != key:
            raise ValueError(
                "Sector reduction requires a hedge explicitly classified in that sector"
            )
        current = next(
            (row for row in data["exposures"].get(dimension, []) if row.get("name") == key), None
        )
        if current is None or current.get("weight") is None:
            raise ValueError("Requested exposure bucket is unavailable")
        requested = (Decimal(str(request.target)) - Decimal(str(current["weight"]))) * Decimal(
            str(nav)
        )
    unit_value = Decimal(str(price)) * Decimal(str(fx)) * Decimal(str(multiplier))
    units = int(requested / unit_value)
    notional = float(units * unit_value)
    requested = float(requested)
    fees, slippage = (
        float(Decimal(str(abs(notional))) * Decimal(str(rate)) / 10000)
        for rate in (request.fee_bps, request.slippage_bps)
    )
    post_nav = nav - fees - slippage
    if post_nav <= 0 or abs(notional) / nav > 5:
        raise ValueError("Hedge estimate exceeds five times NAV or consumes NAV in costs")
    existing = (
        next(
            (
                float(row["market_value"])
                for row in data["positions"]
                if row["symbol"] == request.symbol
            ),
            0,
        )
        if request.instrument_type == "ETF"
        else 0
    )
    gross_before, net_before = risk.get("gross_exposure"), risk.get("net_exposure")
    beta_after = (
        (beta * nav + (0 if is_currency else notional * hbeta)) / post_nav
        if beta is not None and (is_currency or hbeta is not None)
        else None
    )
    gross_after = (
        (gross_before * nav + (0 if is_currency else abs(existing + notional) - abs(existing)))
        / post_nav
        if gross_before is not None
        else None
    )
    net_after = (
        (net_before * nav + (0 if is_currency else notional)) / post_nav
        if net_before is not None
        else None
    )
    return {
        "mode": request.mode,
        "instrument_type": request.instrument_type,
        "symbol": request.currency if is_currency else request.symbol,
        "direction": "INCREASE" if units > 0 else "DECREASE" if units < 0 else "NO CHANGE",
        "target": request.target,
        "required_notional": requested,
        "signed_notional": notional,
        "units": units,
        "residual_notional": requested - notional,
        "price": price,
        "fx": fx,
        "contract_multiplier": multiplier,
        "hedge_beta": hbeta,
        "pre_nav": nav,
        "post_cost_nav": post_nav,
        "beta_before": beta,
        "beta_after": beta_after,
        "gross_before": gross_before,
        "gross_after": gross_after,
        "net_before": net_before,
        "net_after": net_after,
        "estimated_fees": fees,
        "estimated_slippage": slippage,
        "var_before": risk.get("var_95"),
        "var_after": None,
        "var_effect": None,
        "var_state": "UNAVAILABLE",
        "equity_stress_impact": None if is_currency or hbeta is None else notional * hbeta * -0.1,
        "currency_stress_impact": notional * 0.05 if is_currency else None,
        "state": "MANUAL REVIEW REQUIRED",
        "review_state": "DRAFT",
        "warnings": [
            WARNING,
            "Indicative exposure only. Borrow availability, margin, basis risk, financing, liquidity and taxes are not modelled. Fees and slippage are editable assumptions.",
            "Post-cost beta and exposure use reduced NAV. Stress impact is an incremental linear -10% equity or +5% currency scenario, not a forecast.",
        ],
    }


class HedgeService:
    def __init__(self, session):
        self.session = session

    def create(self, portfolio: str, request: HedgeRequest, actor: str) -> dict:
        data = PortfolioValuationService(self.session).latest(portfolio, commit=False)
        now = datetime.now(UTC)
        end = (
            close_of_day(datetime.fromisoformat(data["curve"][-1]["date"]).date())
            if data.get("curve")
            else now
        )
        fx_resolver = FxRateResolver(self.session)
        base = data["portfolio"]["base_currency"]
        frame = pd.DataFrame()
        settings = RiskSettings.model_validate(data.get("risk_model", {}).get("settings", {}))
        benchmark = self.session.scalar(
            select(models.Instrument).where(models.Instrument.symbol == "SPY")
        )
        if request.instrument_type == "ETF":
            item = self.session.scalar(
                select(models.Instrument).where(models.Instrument.symbol == request.symbol)
            )
            if item is None or item.asset_class != "ETF":
                raise ValueError("Select a registered ETF with marked data")
            ids = {row["instrument_id"] for row in data["positions"]} | {item.id}
            if benchmark:
                ids.add(benchmark.id)
            instruments = {
                row.id: row
                for row in self.session.scalars(
                    select(models.Instrument).where(models.Instrument.id.in_(ids))
                )
            }
            prices = MarketPriceResolver(self.session, list(ids))
            price = prices.resolve(item.id, end)
            fx, fx_provenance = fx_resolver.resolve(item.currency, base, end)
            if price is None or fx is None:
                raise ValueError("Hedge quote and currency FX marks are required")
            histories = {}
            for key in ids:
                histories[key] = {}
                for day in data["curve"]:
                    stamp = close_of_day(datetime.fromisoformat(day["date"]).date())
                    mark = prices.resolve(key, stamp)
                    rate, _ = fx_resolver.resolve(instruments[key].currency, base, stamp)
                    histories[key][stamp] = float(mark.value * rate) if mark and rate else None
            frame = pd.DataFrame(histories).sort_index()
            beta_result = calculate_risk(
                frame, pd.Series({item.id: 1.0}), 1, benchmark.id if benchmark else None, settings
            )
            hedge = {
                "id": item.id,
                "price": float(price.value),
                "fx": float(fx),
                "multiplier": 1,
                "beta": beta_result.metrics["beta"],
                "sector": item.sector,
                "price_provenance": prices.describe(item.id, end),
                "fx_provenance": fx_provenance,
                "beta_model": beta_result.evidence,
            }
        else:
            fx, fx_provenance = fx_resolver.resolve(request.currency, base, end)
            if fx is None:
                raise ValueError("Estimate requires a recorded FX mark")
            if request.instrument_type == "FX_CONVERSION":
                if request.currency == base:
                    raise ValueError("Select a non-base currency")
                hedge = {
                    "price": 1,
                    "fx": float(fx),
                    "multiplier": 1,
                    "beta": None,
                    "fx_provenance": fx_provenance,
                }
            else:
                if any(
                    value is None
                    for value in (
                        request.assumed_price,
                        request.assumed_beta,
                        request.contract_multiplier,
                    )
                ):
                    raise ValueError(
                        "Futures estimates require explicit price, beta and contract multiplier assumptions"
                    )
                hedge = {
                    "price": request.assumed_price,
                    "fx": float(fx),
                    "multiplier": request.contract_multiplier,
                    "beta": request.assumed_beta,
                    "fx_provenance": fx_provenance,
                    "price_provenance": {
                        "data_state": "USER ASSUMPTION",
                        "source": "Manual futures estimate",
                    },
                }
        result = size_hedge(data, request, hedge)
        if not frame.empty:
            weights = pd.Series(
                {
                    row["instrument_id"]: float(row["market_value"]) / result["post_cost_nav"]
                    for row in data["positions"]
                },
                dtype=float,
            )
            weights[hedge["id"]] = (
                weights.get(hedge["id"], 0) + result["signed_notional"] / result["post_cost_nav"]
            )
            after = calculate_risk(
                frame,
                weights,
                result["post_cost_nav"],
                benchmark.id if benchmark else None,
                settings,
            )
            result["var_after"] = after.metrics["var_95"]
            result["var_state"] = after.evidence["state"]
            result["var_effect"] = (
                result["var_after"] - result["var_before"]
                if result["var_after"] is not None and result["var_before"] is not None
                else None
            )
            result["risk_after_model"] = after.evidence
        result.update(
            {
                "source": data["source"],
                "quality": data["quality"],
                "as_of": data["as_of"],
                "calculated_at": now.isoformat(),
                "valuation_run_id": data["valuation_run_id"],
                "portfolio_id": data["portfolio"]["id"],
                "calculation_version": "knk-hedge-1.0",
                "hedge_inputs": hedge,
            }
        )
        run = models.AnalysisRun(
            kind="hedge",
            name=f"{request.mode} / {request.symbol}",
            status="SUCCEEDED",
            parameters={
                **request.model_dump(),
                "_portfolio": data,
                "portfolio_id": data["portfolio"]["id"],
            },
            result=result,
            history=[{"state": "DRAFT", "at": now.isoformat(), "actor": actor}],
            started_at=now,
            finished_at=now,
        )
        self.session.add(run)
        self.session.flush()
        audit(
            self.session,
            "HEDGE_ANALYSIS_CREATED",
            "analysis_run",
            run.id,
            {"valuation_run_id": data["valuation_run_id"], "parameters": request.model_dump()},
            actor,
        )
        return {"id": run.id, **result}

    def review(self, portfolio: str, run_id: str, state: str, reason: str, actor: str):
        book, _ = PortfolioValuationService(self.session).portfolio(portfolio)
        run = self.session.get(models.AnalysisRun, run_id)
        if run is None or run.kind != "hedge" or run.parameters.get("portfolio_id") != book.id:
            raise ValueError("Hedge analysis not found in this portfolio")
        before = run.result["review_state"]
        run.result = {**run.result, "review_state": state}
        run.history = [
            *run.history,
            {"state": state, "at": datetime.now(UTC).isoformat(), "actor": actor, "reason": reason},
        ]
        audit(
            self.session,
            "HEDGE_REVIEWED",
            "analysis_run",
            run.id,
            {"before": before, "after": state, "reason": reason},
            actor,
        )
        return {"id": run.id, **run.result}
