"""Source-aware chain analytics and configurable, explicitly assumed OI positioning."""

import math
from collections import defaultdict
from datetime import UTC, datetime
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from vollib.black_scholes_merton.greeks.analytical import gamma as model_gamma

from .option_contracts import ChainContract
from .option_greeks import UNITS, PricingInputs, greeks, implied_iv


class OptionLeg(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    option_symbol: str = Field(min_length=1, max_length=120)
    quantity: float = Field(ge=-1e6, le=1e6)
    premium: float | None = Field(default=None, ge=0, le=1e9)


class OptionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    symbol: str = Field(min_length=1, max_length=40)
    dataset_version_id: str | None = None
    as_of: datetime | None = None
    spot_override: float | None = Field(default=None, gt=0, le=1e9)
    risk_free: float = Field(default=0.03, ge=-0.2, le=1)
    dividend_yield: float = Field(default=0, ge=0, le=1)
    greek_source: Literal["CALCULATED", "PROVIDER"] = "CALCULATED"
    dealer_sign: Literal["DEALER_SHORT", "NEUTRAL", "CALL_POSITIVE_PUT_NEGATIVE"] = "DEALER_SHORT"
    allow_american_approximation: bool = False
    max_age_hours: float = Field(default=72, gt=0, le=8760)
    expiry: str | None = None
    profile_low: float = Field(default=0.8, ge=0.1, lt=1)
    profile_high: float = Field(default=1.2, gt=1, le=3)
    portfolio: str | None = None
    legs: list[OptionLeg] = Field(default_factory=list, max_length=20)


def dealer_sign(right, convention):
    if convention == "DEALER_SHORT":
        return -1
    if convention == "NEUTRAL":
        return 1
    return 1 if right == "CALL" else -1


def _sum(rows, key):
    values = [row[key] for row in rows if row.get(key) is not None]
    return sum(values) if values else None


def _ratio(a, b):
    return a / b if a is not None and b is not None and b > 0 else None


def analyse_chain(
    contracts: list[ChainContract], config: OptionsRequest, spot: float, as_of: datetime
):
    if as_of.tzinfo is None or as_of > datetime.now(UTC):
        raise ValueError("Options as-of must be a timezone-aware present or historical instant")
    if not math.isfinite(spot) or spot <= 0:
        raise ValueError("Positive finite spot price required")
    if not contracts or len(contracts) > 2000:
        raise ValueError("Select between one and 2,000 chain observations")
    chosen = {}
    identities = {}
    for row in contracts:
        if row.symbol.upper() != config.symbol.upper() or (
            config.expiry and row.expiry.isoformat() != config.expiry
        ):
            continue
        identity = (row.strike, row.right, row.expiry, row.multiplier, row.currency)
        if row.option_symbol in identities and identities[row.option_symbol] != identity:
            raise ValueError("An option symbol has conflicting contract specifications")
        identities[row.option_symbol] = identity
        if row.timestamp <= as_of and (
            row.option_symbol not in chosen or chosen[row.option_symbol].timestamp < row.timestamp
        ):
            chosen[row.option_symbol] = row
    if not chosen:
        raise ValueError("No matching chain observations are available as of the selected instant")
    if len({row.currency for row in chosen.values()}) != 1:
        raise ValueError("Selected chain cannot mix quote currencies")
    rows, profile_inputs = [], []
    for contract in sorted(chosen.values(), key=lambda row: (row.expiry, row.strike, row.right)):
        row = contract.model_dump(mode="json")
        years = (contract.expires_at - as_of).total_seconds() / (365 * 86400)
        age = (as_of - contract.timestamp).total_seconds() / 3600
        row.update(
            {
                "age_hours": age,
                "years": years,
                "mid": (contract.bid + contract.ask) / 2
                if contract.bid is not None and contract.ask is not None
                else None,
                "state": "CALCULATED",
                "greek_source": config.greek_source,
            }
        )
        option_price = row["mid"] if row["mid"] is not None else contract.last
        intrinsic = max(0, (spot - contract.strike) * (1 if contract.right == "CALL" else -1))
        row.update(
            {
                "intrinsic": intrinsic,
                "extrinsic": option_price - intrinsic if option_price is not None else None,
                "moneyness": spot / contract.strike,
                "iv": contract.volatility,
                "iv_unit": "DECIMAL",
            }
        )
        provider = {
            key: getattr(contract, key) for key in ("delta", "gamma", "theta", "vega", "rho")
        }
        row["provider_greeks"] = provider
        row.update({key: None for key in UNITS})
        row.update(
            {
                "gex": None,
                "dex": None,
                "contract_gamma": None,
                "dollar_gamma": None,
                "theoretical_price": None,
                "reason": None,
            }
        )
        if years <= 0:
            row.update(state="EXPIRED", reason="No pre-expiry Greeks for an expired contract")
        elif age > config.max_age_hours:
            row.update(state="STALE", reason="Observation exceeds selected maximum age")
        else:
            can_model = contract.exercise_style == "EUROPEAN" or config.allow_american_approximation
            assumptions = PricingInputs(
                right=contract.right,
                spot=spot,
                strike=contract.strike,
                years=years,
                risk_free=config.risk_free,
                dividend_yield=config.dividend_yield,
                volatility=contract.volatility or 0.2,
            )
            if contract.volatility is None and can_model and option_price is not None:
                try:
                    row["iv"] = implied_iv(option_price, assumptions)
                    row["iv_source"] = (
                        "CALCULATED FROM MID" if row["mid"] is not None else "CALCULATED FROM LAST"
                    )
                except ValueError as exc:
                    row["reason"] = str(exc)
            else:
                row["iv_source"] = "SOURCE OBSERVATION" if contract.volatility else "UNAVAILABLE"
            if row["iv"] is not None:
                assumptions = assumptions.model_copy(update={"volatility": row["iv"]})
            if config.greek_source == "PROVIDER":
                if contract.greek_units == "STANDARD":
                    row.update(provider)
                    row["state"] = (
                        "PROVIDER SUPPLIED"
                        if all(v is not None for v in provider.values())
                        else "PARTIAL_DATA"
                    )
                else:
                    row.update(
                        state="UNAVAILABLE",
                        reason="Provider Greeks need explicit STANDARD unit declaration",
                    )
            elif not can_model:
                row.update(
                    state="UNAVAILABLE",
                    reason="American exercise requires explicit European BSM approximation consent",
                )
            elif row["iv"] is None:
                row.update(
                    state="UNAVAILABLE",
                    reason=row["reason"]
                    or "Neither valid implied volatility nor a solvable option quote is available",
                )
            else:
                row.update(greeks(assumptions))
                row["state"] = (
                    "CALCULATED" if contract.exercise_style == "EUROPEAN" else "BSM APPROXIMATION"
                )
            if row["gamma"] is not None:
                row["contract_gamma"] = row["gamma"] * contract.multiplier
                row["dollar_gamma"] = row["contract_gamma"] * spot**2
            sign = dealer_sign(contract.right, config.dealer_sign)
            if contract.open_interest is not None:
                row["gex"] = (
                    sign * contract.open_interest * row["dollar_gamma"] * 0.01
                    if row["dollar_gamma"] is not None
                    else None
                )
                row["dex"] = (
                    sign * contract.open_interest * row["delta"] * contract.multiplier * spot
                    if row["delta"] is not None
                    else None
                )
                if row["iv"] is not None and can_model:
                    profile_inputs.append((contract, assumptions, sign))
            row["pricing_assumptions"] = (
                assumptions.model_dump() if can_model and row["iv"] is not None else None
            )
        rows.append(row)
    by_strike, by_expiry = [], []
    for key, target in (("strike", by_strike), ("expiry", by_expiry)):
        buckets = defaultdict(list)
        for row in rows:
            buckets[row[key]].append(row)
        for value, members in sorted(buckets.items()):
            calls, puts = (
                [r for r in members if r["right"] == "CALL"],
                [r for r in members if r["right"] == "PUT"],
            )
            target.append(
                {
                    key: value,
                    "call_gex": _sum(calls, "gex"),
                    "put_gex": _sum(puts, "gex"),
                    "net_gex": _sum(members, "gex"),
                    "dex": _sum(members, "dex"),
                    "contracts": len(members),
                    "included": sum(r["gex"] is not None for r in members),
                }
            )
    profile = []
    for candidate in np.linspace(spot * config.profile_low, spot * config.profile_high, 41):
        calls, puts = [], []
        for contract, inputs, sign in profile_inputs:
            gamma = float(
                model_gamma(
                    "c" if contract.right == "CALL" else "p",
                    candidate,
                    inputs.strike,
                    inputs.years,
                    inputs.risk_free,
                    inputs.volatility,
                    inputs.dividend_yield,
                )
            )
            value = (
                sign * contract.open_interest * gamma * contract.multiplier * candidate**2 * 0.01
            )
            (calls if contract.right == "CALL" else puts).append(value)
        profile.append(
            {
                "spot": float(candidate),
                "call_gex": sum(calls) if calls else None,
                "put_gex": sum(puts) if puts else None,
                "net_gex": sum(calls + puts) if calls or puts else None,
            }
        )
    flips = []
    for left, right in zip(profile, profile[1:], strict=False):
        a, b = left["net_gex"], right["net_gex"]
        if a is not None and b is not None and a * b < 0:
            flips.append(left["spot"] - a * (right["spot"] - left["spot"]) / (b - a))
    valid = [row for row in rows if row["state"] not in {"EXPIRED", "STALE"}]
    calls = [row for row in valid if row["right"] == "CALL"]
    puts = [row for row in valid if row["right"] == "PUT"]
    abs_gex = sum(abs(row["gex"]) for row in rows if row["gex"] is not None)

    def wall(key):
        values = [row for row in by_strike if row[key] is not None and abs(row[key]) > 0]
        return max(values, key=lambda row: abs(row[key]))["strike"] if values else None

    max_pain, expected_moves, skew = [], [], []
    for expiry in sorted({row["expiry"] for row in valid}):
        contracts_at = [row for row in valid if row["expiry"] == expiry]
        covered = [row for row in contracts_at if row["open_interest"] is not None]
        strikes = sorted({row["strike"] for row in covered})
        payouts = [
            {
                "strike": level,
                "payout": sum(
                    max(0, (level - row["strike"]) * (1 if row["right"] == "CALL" else -1))
                    * row["open_interest"]
                    * row["multiplier"]
                    for row in covered
                ),
            }
            for level in strikes
        ]
        complete_oi = len(covered) == len(contracts_at)
        nonzero_oi = sum(row["open_interest"] for row in covered) > 0
        best = (
            min(payouts, key=lambda row: row["payout"])
            if payouts and complete_oi and nonzero_oi
            else None
        )
        max_pain.append(
            {
                "expiry": expiry,
                "strike": best["strike"] if best else None,
                "payout": best["payout"] if best else None,
                "state": "OI PAYOUT ESTIMATE" if best else "INSUFFICIENT_DATA",
            }
        )
        with_iv = [row for row in contracts_at if row["iv"] is not None]
        closest = min(with_iv, key=lambda row: abs(row["strike"] - spot)) if with_iv else None
        expected_moves.append(
            {
                "expiry": expiry,
                "atm_strike": closest["strike"] if closest else None,
                "iv": closest["iv"] if closest else None,
                "move": spot * closest["iv"] * math.sqrt(closest["years"]) if closest else None,
            }
        )
        delta_calls = [
            row for row in with_iv if row["right"] == "CALL" and row["delta"] is not None
        ]
        delta_puts = [row for row in with_iv if row["right"] == "PUT" and row["delta"] is not None]
        call25 = min(delta_calls, key=lambda row: abs(row["delta"] - 0.25)) if delta_calls else None
        put25 = min(delta_puts, key=lambda row: abs(row["delta"] + 0.25)) if delta_puts else None
        covered25 = (
            call25 is not None
            and put25 is not None
            and abs(call25["delta"] - 0.25) <= 0.1
            and abs(put25["delta"] + 0.25) <= 0.1
        )
        skew.append(
            {
                "expiry": expiry,
                "call_delta": call25["delta"] if call25 else None,
                "put_delta": put25["delta"] if put25 else None,
                "risk_reversal": call25["iv"] - put25["iv"] if covered25 else None,
                "butterfly": (call25["iv"] + put25["iv"]) / 2 - closest["iv"]
                if covered25 and closest
                else None,
                "state": "NEAREST OBSERVED 25 DELTA" if covered25 else "INSUFFICIENT_DATA",
            }
        )
    included = sum(row["gex"] is not None for row in rows)
    total = len(rows)
    return {
        "symbol": config.symbol.upper(),
        "currency": next(iter(chosen.values())).currency,
        "spot": spot,
        "items": rows,
        "by_strike": by_strike,
        "by_expiry": by_expiry,
        "spot_profile": profile,
        "gamma_flips": flips,
        "gamma_flip": min(flips, key=lambda value: abs(value - spot)) if flips else None,
        "max_pain": max_pain,
        "expected_moves": expected_moves,
        "skew": skew,
        "iv_surface": [
            {
                "strike": row["strike"],
                "expiry": row["expiry"],
                "days": row["years"] * 365,
                "iv": row["iv"],
                "right": row["right"],
            }
            for row in valid
            if row["iv"] is not None
        ],
        "summary": {
            "net_gex": _sum(rows, "gex"),
            "call_gex": _sum(calls, "gex"),
            "put_gex": _sum(puts, "gex"),
            "dex": _sum(rows, "dex"),
            "call_wall": wall("call_gex"),
            "put_wall": wall("put_gex"),
            "largest_positive_gamma": max(
                (
                    row["net_gex"]
                    for row in by_strike
                    if row["net_gex"] is not None and row["net_gex"] > 0
                ),
                default=None,
            ),
            "largest_negative_gamma": min(
                (
                    row["net_gex"]
                    for row in by_strike
                    if row["net_gex"] is not None and row["net_gex"] < 0
                ),
                default=None,
            ),
            "gamma_concentration": max(
                (abs(row["gex"]) / abs_gex for row in rows if row["gex"] is not None), default=None
            )
            if abs_gex
            else None,
            "put_call_oi": _ratio(_sum(puts, "open_interest"), _sum(calls, "open_interest"))
            if all(row["open_interest"] is not None for row in valid)
            else None,
            "put_call_volume": _ratio(_sum(puts, "volume"), _sum(calls, "volume"))
            if all(row["volume"] is not None for row in valid)
            else None,
        },
        "coverage": {
            "contracts": total,
            "gex_included": included,
            "missing_gex": total - included,
            "gex_fraction": included / total if total else 0,
            "spot_profile_contracts": len(profile_inputs),
            "confidence": "LOW: DEALER INVENTORY UNOBSERVED",
        },
        "state": "CALCULATED"
        if included == total
        else "PARTIAL_DATA"
        if included
        else "UNAVAILABLE",
        "greek_units": UNITS,
        "dealer_sign": config.dealer_sign,
        "calculation_version": "knk-options-1.0 / vollib 1.0.11",
        "as_of": as_of.isoformat(),
        "warnings": [
            "OI sign conventions are research assumptions, not confirmed dealer inventory or trading signals.",
            "GEX = signed OI x gamma x multiplier x spot squared x 0.01; this is hedge-flow exposure per 1% spot move, not gamma P&L.",
            "BSM uses continuous dividend yield, ACT/365 and fixed IV. No discrete dividend, early-exercise or smile dynamics are modelled.",
            "Advanced Greeks are central finite differences of vollib analytical Greeks; sensitivity units are explicit. Near-expiry values can be unstable.",
            "Spot profiles always reprice using BSM, including when current Greeks are provider-supplied. Flip levels interpolate sign changes within the sampled range only.",
            "Max pain minimizes OI settlement payout at listed strikes; it is not a price forecast. Expected move is ATM IV x spot x sqrt(time), not a guaranteed probability interval.",
            "OI changes are reported observations, not inferred intraday trading flow. Missing contracts mean partial-chain aggregates.",
            "Skew uses nearest observed +/-25 delta contracts within a 0.10 delta tolerance; no fixed-delta interpolation is claimed.",
        ],
    }


def position_analytics(result, legs: list[OptionLeg], equity_quantity=0):
    lookup = {row["option_symbol"]: row for row in result["items"]}
    rows = []
    for leg in legs:
        contract = lookup.get(leg.option_symbol)
        if not contract:
            rows.append(
                {
                    "option_symbol": leg.option_symbol,
                    "quantity": leg.quantity,
                    "state": "MISSING CONTRACT",
                }
            )
            continue
        row = {
            "option_symbol": leg.option_symbol,
            "quantity": leg.quantity,
            "state": contract["state"],
            "multiplier": contract["multiplier"],
            "expiry": contract["expiry"],
        }
        for greek in ("delta", "gamma", "theta", "vega", "rho"):
            row[greek] = (
                contract[greek] * leg.quantity * contract["multiplier"]
                if contract[greek] is not None
                else None
            )
        row["dollar_delta"] = row["delta"] * result["spot"] if row["delta"] is not None else None
        row["gamma_1pct"] = (
            row["gamma"] * result["spot"] ** 2 * 0.01 if row["gamma"] is not None else None
        )
        row["premium"] = (
            leg.premium
            if leg.premium is not None
            else contract["mid"]
            if contract["mid"] is not None
            else contract["last"]
        )
        rows.append(row)
    complete = all(
        all(row.get(greek) is not None for greek in ("delta", "gamma", "theta", "vega", "rho"))
        for row in rows
    )
    totals = {
        key: _sum(rows, key) if rows else 0
        for key in ("delta", "gamma", "theta", "vega", "rho", "dollar_delta", "gamma_1pct")
    }
    if totals["delta"] is not None:
        totals["delta"] += equity_quantity
        totals["dollar_delta"] += equity_quantity * result["spot"]
    curves = []
    expiries = {row.get("expiry") for row in rows}
    can_payoff = rows and len(expiries) == 1 and all(row.get("premium") is not None for row in rows)
    if can_payoff:
        for spot in np.linspace(result["spot"] * 0.5, result["spot"] * 1.5, 101):
            pnl = equity_quantity * (spot - result["spot"])
            for row in rows:
                contract = lookup[row["option_symbol"]]
                intrinsic = max(
                    0, (spot - contract["strike"]) * (1 if contract["right"] == "CALL" else -1)
                )
                pnl += (intrinsic - row["premium"]) * row["quantity"] * row["multiplier"]
            curves.append({"spot": float(spot), "pnl": float(pnl)})
    return {
        "items": rows,
        "totals": totals,
        "state": "COMPLETE" if complete else "PARTIAL_DATA",
        "equity_quantity": equity_quantity,
        "payoff": curves,
        "payoff_state": "SINGLE EXPIRY PAYOFF" if curves else "UNAVAILABLE",
        "warnings": [
            "Position quantities are signed contracts; chain open interest is never substituted for owned positions.",
            "Totals are for the selected underlying and quote currency only, not an FX-converted whole-portfolio risk number.",
            "Payoff uses explicit entry premium or observed current mid/last; equity starts at the selected spot. No fees or early assignment; mixed expiries are unavailable.",
        ],
    }
