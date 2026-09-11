"""Source-aware chain analytics and configurable, explicitly assumed OI positioning."""

import math
from collections import defaultdict
from collections.abc import Callable, Iterable
from datetime import UTC, date, datetime, time
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter
from vollib.black_scholes_merton.greeks.analytical import gamma as model_gamma

from .option_contracts import ChainContract
from .option_greeks import UNITS, PricingInputs, greeks, implied_iv
from .options_results import (
    AnalysedOption,
    ChainAnalysis,
    CoreGreek,
    DealerConvention,
    ExpectedMove,
    ExpiryExposure,
    ExposureTotals,
    MaxPain,
    OptionPosition,
    OptionSkew,
    PayoffPoint,
    PositionAnalysis,
    PositionMetric,
    ProviderGreeks,
    SpotExposure,
    StrikeExposure,
)

OPTION_ROW = TypeAdapter(AnalysedOption)
CORE_GREEKS: tuple[CoreGreek, ...] = ("delta", "gamma", "theta", "vega", "rho")
POSITION_METRICS: tuple[PositionMetric, ...] = (*CORE_GREEKS, "dollar_delta", "gamma_1pct")
type ModelMetric = Literal[
    "delta",
    "gamma",
    "theta",
    "vega",
    "rho",
    "vanna",
    "charm",
    "vomma",
    "speed",
    "color",
    "veta",
    "zomma",
    "ultima",
    "theoretical_price",
]
MODEL_METRICS: tuple[ModelMetric, ...] = (
    *CORE_GREEKS,
    "vanna",
    "charm",
    "vomma",
    "speed",
    "color",
    "veta",
    "zomma",
    "ultima",
    "theoretical_price",
)
type ContractIdentity = tuple[float, str, date, float, str, str, time]


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
    dealer_sign: DealerConvention = "DEALER_SHORT"
    allow_american_approximation: bool = False
    max_age_hours: float = Field(default=72, gt=0, le=8760)
    expiry: str | None = None
    profile_low: float = Field(default=0.8, ge=0.1, lt=1)
    profile_high: float = Field(default=1.2, gt=1, le=3)
    portfolio: str | None = None
    legs: list[OptionLeg] = Field(default_factory=list, max_length=20)


def dealer_sign(right: Literal["CALL", "PUT"], convention: DealerConvention) -> int:
    if convention == "DEALER_SHORT":
        return -1
    if convention == "NEUTRAL":
        return 1
    return 1 if right == "CALL" else -1


def _sum(values: Iterable[float | None]) -> float | None:
    available = [value for value in values if value is not None]
    return sum(available) if available else None


def _ratio(a: float | None, b: float | None) -> float | None:
    return a / b if a is not None and b is not None and b > 0 else None


def _exposure_groups[T: (float, str)](
    rows: list[AnalysedOption], key: Callable[[AnalysedOption], T]
) -> list[tuple[T, ExposureTotals]]:
    buckets: dict[T, list[AnalysedOption]] = defaultdict(list)
    for row in rows:
        buckets[key(row)].append(row)
    groups: list[tuple[T, ExposureTotals]] = []
    for value, members in sorted(buckets.items()):
        groups.append(
            (
                value,
                {
                    "call_gex": _sum(r["gex"] for r in members if r["right"] == "CALL"),
                    "put_gex": _sum(r["gex"] for r in members if r["right"] == "PUT"),
                    "net_gex": _sum(r["gex"] for r in members),
                    "dex": _sum(r["dex"] for r in members),
                    "contracts": len(members),
                    "included": sum(r["gex"] is not None for r in members),
                },
            )
        )
    return groups


def analyse_chain(
    contracts: list[ChainContract], config: OptionsRequest, spot: float, as_of: datetime
) -> ChainAnalysis:
    if as_of.tzinfo is None or as_of > datetime.now(UTC):
        raise ValueError("Options as-of must be a timezone-aware present or historical instant")
    if not math.isfinite(spot) or spot <= 0:
        raise ValueError("Positive finite spot price required")
    if not contracts or len(contracts) > 2000:
        raise ValueError("Select between one and 2,000 chain observations")
    chosen: dict[str, ChainContract] = {}
    identities: dict[str, ContractIdentity] = {}
    for observation in contracts:
        if observation.timestamp > as_of:
            continue
        if observation.symbol.upper() != config.symbol.upper() or (
            config.expiry and observation.expiry.isoformat() != config.expiry
        ):
            continue
        identity = (
            observation.strike,
            observation.right,
            observation.expiry,
            observation.multiplier,
            observation.currency,
            observation.exercise_style,
            observation.expiry_time_utc,
        )
        if (
            observation.option_symbol in identities
            and identities[observation.option_symbol] != identity
        ):
            raise ValueError("An option symbol has conflicting contract specifications")
        identities[observation.option_symbol] = identity
        if (
            observation.option_symbol not in chosen
            or chosen[observation.option_symbol].timestamp < observation.timestamp
        ):
            chosen[observation.option_symbol] = observation
    if not chosen:
        raise ValueError("No matching chain observations are available as of the selected instant")
    if len({row.currency for row in chosen.values()}) != 1:
        raise ValueError("Selected chain cannot mix quote currencies")
    rows: list[AnalysedOption] = []
    profile_inputs: list[tuple[ChainContract, PricingInputs, int, int]] = []
    for contract in sorted(chosen.values(), key=lambda row: (row.expiry, row.strike, row.right)):
        years = (contract.expires_at - as_of).total_seconds() / (365 * 86400)
        age = (as_of - contract.timestamp).total_seconds() / 3600
        mid = (
            (contract.bid + contract.ask) / 2
            if contract.bid is not None and contract.ask is not None
            else None
        )
        option_price = mid if mid is not None else contract.last
        intrinsic = max(0, (spot - contract.strike) * (1 if contract.right == "CALL" else -1))
        provider: ProviderGreeks = {
            "delta": contract.delta,
            "gamma": contract.gamma,
            "theta": contract.theta,
            "vega": contract.vega,
            "rho": contract.rho,
        }
        row = OPTION_ROW.validate_python(
            {
                **contract.model_dump(mode="json"),
                "age_hours": age,
                "years": years,
                "mid": mid,
                "state": "CALCULATED",
                "greek_source": config.greek_source,
                "intrinsic": intrinsic,
                "extrinsic": option_price - intrinsic if option_price is not None else None,
                "moneyness": spot / contract.strike,
                "iv": contract.volatility,
                "iv_unit": "DECIMAL",
                "provider_greeks": provider,
                **dict.fromkeys(UNITS),
                "gex": None,
                "dex": None,
                "contract_gamma": None,
                "dollar_gamma": None,
                "theoretical_price": None,
                "reason": None,
            },
            strict=True,
        )
        if years <= 0:
            row["state"] = "EXPIRED"
            row["reason"] = "No pre-expiry Greeks for an expired contract"
        elif age > config.max_age_hours:
            row["state"] = "STALE"
            row["reason"] = "Observation exceeds selected maximum age"
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
                    for greek in CORE_GREEKS:
                        row[greek] = provider[greek]
                    row["state"] = (
                        "PROVIDER SUPPLIED"
                        if all(v is not None for v in provider.values())
                        else "PARTIAL_DATA"
                    )
                else:
                    row["state"] = "UNAVAILABLE"
                    row["reason"] = "Provider Greeks need explicit STANDARD unit declaration"
            elif not can_model:
                row["state"] = "UNAVAILABLE"
                row["reason"] = (
                    "American exercise requires explicit European BSM approximation consent"
                )
            elif row["iv"] is None:
                row["state"] = "UNAVAILABLE"
                row["reason"] = (
                    row["reason"]
                    or "Neither valid implied volatility nor a solvable option quote is available"
                )
            else:
                calculated = greeks(assumptions)
                for metric in MODEL_METRICS:
                    row[metric] = calculated.get(metric)
                row["state"] = (
                    "CALCULATED" if contract.exercise_style == "EUROPEAN" else "BSM APPROXIMATION"
                )
            if row["gamma"] is not None:
                contract_gamma = row["gamma"] * contract.multiplier
                row["contract_gamma"] = contract_gamma
                row["dollar_gamma"] = contract_gamma * spot**2
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
                    profile_inputs.append((contract, assumptions, sign, contract.open_interest))
            row["pricing_assumptions"] = (
                assumptions.model_dump() if can_model and row["iv"] is not None else None
            )
        rows.append(row)
    by_strike: list[StrikeExposure] = [
        {"strike": value, **totals}
        for value, totals in _exposure_groups(rows, lambda row: row["strike"])
    ]
    by_expiry: list[ExpiryExposure] = [
        {"expiry": value, **totals}
        for value, totals in _exposure_groups(rows, lambda row: row["expiry"])
    ]
    profile: list[SpotExposure] = []
    # Retain NumPy accumulation before JSON conversion so profile values remain exact.
    for candidate in np.linspace(spot * config.profile_low, spot * config.profile_high, 41):
        call_values: list[np.float64] = []
        put_values: list[np.float64] = []
        for contract, inputs, sign, open_interest in profile_inputs:
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
            value = sign * open_interest * gamma * contract.multiplier * candidate**2 * 0.01
            (call_values if contract.right == "CALL" else put_values).append(np.float64(value))
        profile.append(
            {
                "spot": float(candidate),
                "call_gex": float(sum(call_values)) if call_values else None,
                "put_gex": float(sum(put_values)) if put_values else None,
                "net_gex": float(sum(call_values + put_values))
                if call_values or put_values
                else None,
            }
        )
    flips: list[float] = []
    for left, right in zip(profile, profile[1:], strict=False):
        a, b = left["net_gex"], right["net_gex"]
        if a is not None and b is not None and a * b < 0:
            flips.append(left["spot"] - a * (right["spot"] - left["spot"]) / (b - a))
    valid = [row for row in rows if row["state"] not in {"EXPIRED", "STALE"}]
    calls = [row for row in valid if row["right"] == "CALL"]
    puts = [row for row in valid if row["right"] == "PUT"]
    abs_gex = sum(abs(row["gex"]) for row in rows if row["gex"] is not None)

    def wall(key: Literal["call_gex", "put_gex"]) -> float | None:
        values = [
            (abs(value), row["strike"])
            for row in by_strike
            if (value := row[key]) is not None and abs(value) > 0
        ]
        return max(values, key=lambda item: item[0])[1] if values else None

    max_pain: list[MaxPain] = []
    expected_moves: list[ExpectedMove] = []
    skew: list[OptionSkew] = []
    for expiry in sorted({row["expiry"] for row in valid}):
        contracts_at = [row for row in valid if row["expiry"] == expiry]
        covered = [(row, oi) for row in contracts_at if (oi := row["open_interest"]) is not None]
        strikes = sorted({row["strike"] for row, _ in covered})
        payouts = [
            {
                "strike": level,
                "payout": sum(
                    max(0, (level - row["strike"]) * (1 if row["right"] == "CALL" else -1))
                    * oi
                    * row["multiplier"]
                    for row, oi in covered
                ),
            }
            for level in strikes
        ]
        complete_oi = len(covered) == len(contracts_at)
        nonzero_oi = sum(oi for _, oi in covered) > 0
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
        with_iv = [(row, iv) for row in contracts_at if (iv := row["iv"]) is not None]
        closest = min(with_iv, key=lambda item: abs(item[0]["strike"] - spot)) if with_iv else None
        expected_moves.append(
            {
                "expiry": expiry,
                "atm_strike": closest[0]["strike"] if closest else None,
                "iv": closest[1] if closest else None,
                "move": spot * closest[1] * math.sqrt(closest[0]["years"]) if closest else None,
            }
        )
        delta_calls = [
            (iv, delta)
            for row, iv in with_iv
            if row["right"] == "CALL" and (delta := row["delta"]) is not None
        ]
        delta_puts = [
            (iv, delta)
            for row, iv in with_iv
            if row["right"] == "PUT" and (delta := row["delta"]) is not None
        ]
        call25 = min(delta_calls, key=lambda item: abs(item[1] - 0.25)) if delta_calls else None
        put25 = min(delta_puts, key=lambda item: abs(item[1] + 0.25)) if delta_puts else None
        risk_reversal, butterfly = None, None
        state = "INSUFFICIENT_DATA"
        if (
            call25 is not None
            and put25 is not None
            and abs(call25[1] - 0.25) <= 0.1
            and abs(put25[1] + 0.25) <= 0.1
        ):
            risk_reversal = call25[0] - put25[0]
            butterfly = (call25[0] + put25[0]) / 2 - closest[1] if closest else None
            state = "NEAREST OBSERVED 25 DELTA"
        skew.append(
            {
                "expiry": expiry,
                "call_delta": call25[1] if call25 else None,
                "put_delta": put25[1] if put25 else None,
                "risk_reversal": risk_reversal,
                "butterfly": butterfly,
                "state": state,
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
            "net_gex": _sum(row["gex"] for row in rows),
            "call_gex": _sum(row["gex"] for row in calls),
            "put_gex": _sum(row["gex"] for row in puts),
            "dex": _sum(row["dex"] for row in rows),
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
            "put_call_oi": _ratio(
                _sum(row["open_interest"] for row in puts),
                _sum(row["open_interest"] for row in calls),
            )
            if all(row["open_interest"] is not None for row in valid)
            else None,
            "put_call_volume": _ratio(
                _sum(row["volume"] for row in puts), _sum(row["volume"] for row in calls)
            )
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


def position_analytics(
    result: ChainAnalysis, legs: list[OptionLeg], equity_quantity: float = 0
) -> PositionAnalysis:
    if not math.isfinite(equity_quantity):
        raise ValueError("Equity quantity must be finite")
    lookup = {row["option_symbol"]: row for row in result["items"]}
    rows: list[OptionPosition] = []
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
        row: OptionPosition = {
            "option_symbol": leg.option_symbol,
            "quantity": leg.quantity,
            "state": contract["state"],
            "multiplier": contract["multiplier"],
            "expiry": contract["expiry"],
        }
        for greek in CORE_GREEKS:
            value = contract[greek]
            row[greek] = (
                value * leg.quantity * contract["multiplier"] if value is not None else None
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
    complete = all(all(row.get(greek) is not None for greek in CORE_GREEKS) for row in rows)
    totals = {key: _sum(row.get(key) for row in rows) if rows else 0 for key in POSITION_METRICS}
    if totals["delta"] is not None:
        totals["delta"] += equity_quantity
    if totals["dollar_delta"] is not None:
        totals["dollar_delta"] += equity_quantity * result["spot"]
    curves: list[PayoffPoint] = []
    expiries = {row.get("expiry") for row in rows}
    payoff_legs = [
        (lookup[row["option_symbol"]], premium, row["quantity"], multiplier)
        for row in rows
        if (premium := row.get("premium")) is not None
        and (multiplier := row.get("multiplier")) is not None
        and row["option_symbol"] in lookup
    ]
    can_payoff = rows and len(expiries) == 1 and len(payoff_legs) == len(rows)
    if can_payoff:
        for spot in np.linspace(result["spot"] * 0.5, result["spot"] * 1.5, 101):
            pnl = equity_quantity * (spot - result["spot"])
            for contract, premium, quantity, multiplier in payoff_legs:
                intrinsic = max(
                    0, (spot - contract["strike"]) * (1 if contract["right"] == "CALL" else -1)
                )
                pnl += (intrinsic - premium) * quantity * multiplier
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
