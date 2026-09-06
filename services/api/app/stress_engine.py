"""Pinned-portfolio linear stress scenarios; estimates are never execution instructions."""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np

VERSION = "knk-stress-3.0"


def correlation_shocks(data: dict, convergence: float) -> dict[str, float]:
    model = data.get("risk_model", {})
    names = model.get("symbols", [])
    if model.get("state") != "AVAILABLE" or not names:
        raise ValueError("Correlation stress requires a complete covariance model")
    covariance = np.asarray(model["covariance"], dtype=float)
    if covariance.shape != (len(names), len(names)) or not np.isfinite(covariance).all():
        raise ValueError("Invalid pinned covariance matrix")
    if not np.allclose(covariance, covariance.T) or np.linalg.eigvalsh(covariance).min() < -1e-10:
        raise ValueError("Covariance must be symmetric positive semidefinite")
    deviations = np.sqrt(np.maximum(0, np.diag(covariance)))
    stressed = (1 - convergence) * covariance + convergence * np.outer(deviations, deviations)
    positions = {row["symbol"]: row for row in data["positions"]}
    if set(positions) != set(names):
        raise ValueError("Covariance and portfolio securities differ")
    weights = np.array(
        [float(positions[name]["market_value"]) / float(data["portfolio"]["nav"]) for name in names]
    )
    deviation = math.sqrt(max(0, float(weights @ stressed @ weights)))
    shocks = (
        NormalDist().inv_cdf(0.05) * stressed @ weights / deviation
        if deviation
        else np.zeros(len(names))
    )
    return dict(zip(names, shocks.tolist(), strict=True))


def calculate_stress(data: dict, parameters: dict) -> dict:
    if data.get("account_source") == "BROKER":
        raise ValueError(
            "Use the reconciled internal-ledger analytical view, not broker snapshot risk"
        )
    nav = data["portfolio"].get("nav")
    if nav is None or not math.isfinite(float(nav)) or float(nav) <= 0:
        raise ValueError("Stress calculation requires a complete positive NAV")
    nav = float(nav)
    equity = float(parameters.get("equity_shock", -10)) / 100
    fx = float(parameters.get("fx_shock", 0)) / 100
    rates = float(parameters.get("rates_bp", 0)) / 10000
    convergence = float(parameters.get("correlation_convergence", 1))
    scope = parameters.get("scope", "All")
    model = parameters.get("model", "LINEAR")
    if (
        not all(math.isfinite(v) for v in (equity, fx, rates, convergence))
        or not -0.95 <= equity <= 2
        or not -0.95 <= fx <= 2
        or abs(rates) > 0.1
        or not 0 <= convergence <= 1
    ):
        raise ValueError("Shock assumptions exceed permitted bounds")
    if fx and data["portfolio"].get("base_currency", "SGD") != "SGD":
        raise ValueError("USD/SGD stress requires an SGD base portfolio")
    common = {
        "pre_nav": nav,
        "parameters": {k: v for k, v in parameters.items() if not k.startswith("_")},
        "source": data["source"],
        "as_of": data["as_of"],
        "quality": data["quality"],
        "calculation_version": VERSION,
        "valuation_run_id": data.get("valuation_run_id"),
    }
    if scope == "Volatility" or model == "VOLATILITY":
        return {
            **common,
            "state": "UNAVAILABLE",
            "loss": None,
            "impact": None,
            "post_nav": None,
            "contributions": [],
            "warnings": [
                "Direct VIX shock mapping is not defined. A VIX move is not a parallel option-IV move; no zero-loss estimate is inferred."
            ],
        }
    if model not in {"LINEAR", "CORRELATION"}:
        raise ValueError("Unknown stress model")
    if model == "CORRELATION" and any((equity, fx, rates)):
        raise ValueError("Correlation scenario cannot also apply directional shocks")
    shocks = correlation_shocks(data, convergence) if model == "CORRELATION" else {}
    rows = []
    for position in data["positions"]:
        value = position.get("market_value")
        if value is None or not math.isfinite(float(value)):
            raise ValueError("Every position requires a finite marked value")
        value = float(value)
        if "option" in position.get("asset_class", "").lower():
            raise ValueError(
                "Linear security stress does not reprice options; use the options scenario model"
            )
        applies = scope == "All" or scope.lower() == (position.get("sector") or "").lower()
        beta = position.get("beta")
        if equity and applies and (beta is None or not math.isfinite(float(beta))):
            raise ValueError("Equity stress requires sufficient position beta history")
        market_shock = shocks.get(
            position["symbol"], equity * float(beta) if applies and equity else 0
        )
        rate_shock = -16 * rates if position["symbol"] == "TLT" else 0
        currency_shock = fx if position["currency"] == "USD" else 0
        shock = max(-1, (1 + market_shock + rate_shock) * (1 + currency_shock) - 1)
        pnl = round(value * shock, 2)
        market_pnl, rates_pnl, fx_pnl = (
            round(value * s, 2) for s in (market_shock, rate_shock, currency_shock)
        )
        rows.append(
            {
                **{k: position.get(k) for k in ("symbol", "sector", "country", "currency", "beta")},
                "market_value": value,
                "shock": shock,
                "pnl": pnl,
                "post_value": round(value + pnl, 2),
                "fx_impact": fx_pnl,
                "equity_impact": market_pnl,
                "rates_impact": rates_pnl,
                "interaction_impact": round(pnl - market_pnl - rates_pnl - fx_pnl, 2),
                "is_hedge": bool(position.get("is_hedge", False)),
            }
        )
    # Economic cash already includes trade settlement. Manual balance buckets are separate.
    for balance in [*data.get("cash", []), *data.get("exposure_balances", [])]:
        if balance["currency"] != "USD":
            continue
        if balance.get("base_value") is None:
            raise ValueError("Currency stress requires complete balance FX marks")
        value = float(balance["base_value"])
        pnl = round(value * fx, 2)
        rows.append(
            {
                "symbol": "USD " + balance.get("bucket", "CASH").upper(),
                "sector": "Cash / balances",
                "country": "Currency",
                "currency": "USD",
                "beta": 0,
                "market_value": value,
                "shock": fx,
                "pnl": pnl,
                "post_value": round(value + pnl, 2),
                "fx_impact": pnl,
                "equity_impact": 0,
                "rates_impact": 0,
                "interaction_impact": 0,
                "is_hedge": False,
            }
        )
    loss = round(sum(row["pnl"] for row in rows), 2)
    post_nav = round(nav + loss, 2)
    known_beta = all(row["beta"] is not None for row in rows)
    factors = [
        {"factor": name, "pnl": round(sum(row[key] for row in rows), 2)}
        for name, key in (
            ("Correlation" if model == "CORRELATION" else "Equity", "equity_impact"),
            ("Rates", "rates_impact"),
            ("FX", "fx_impact"),
            ("Interaction / floor / rounding", "interaction_impact"),
        )
    ]
    return {
        **common,
        "state": "AVAILABLE",
        "loss": loss,
        "impact": loss / nav,
        "post_nav": post_nav,
        "worst_position": min(rows, key=lambda row: row["pnl"], default={}).get("symbol"),
        "currency_impact": round(sum(row["fx_impact"] for row in rows), 2),
        "contributions": rows,
        "factor_contributions": factors,
        "beta_after": sum(float(row["beta"]) * row["post_value"] for row in rows) / post_nav
        if known_beta and post_nav > 0
        else None,
        "hedge_contribution": round(sum(row["pnl"] for row in rows if row["is_hedge"]), 2)
        if any(row["is_hedge"] for row in rows)
        else None,
        "largest_losses": sorted(rows, key=lambda row: row["pnl"])[:5],
        "warnings": [
            "Scenario estimate, not a forecast. Constant holdings and estimated beta; liquidity, tax and nonlinear option effects excluded.",
            "Rates use assumed duration 16 for TLT only. Hedge attribution requires explicit tagged holdings; short positions are not automatically classified as hedges.",
        ]
        + (
            [
                "One-day normal 95% conditional portfolio tail, zero drift. Covariance is blended toward perfect positive correlation; asset shocks are covariance contributions, not a historical crash."
            ]
            if model == "CORRELATION"
            else []
        ),
    }
