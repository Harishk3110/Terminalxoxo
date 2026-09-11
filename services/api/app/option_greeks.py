"""European BSM via vollib; numerical higher sensitivities retain explicit units."""

import math
from collections.abc import Callable
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from vollib.black_scholes_merton import black_scholes_merton
from vollib.black_scholes_merton.greeks import analytical
from vollib.black_scholes_merton.implied_volatility import implied_volatility

type GreekMetric = Literal["delta", "gamma", "theta", "vega", "rho"]
type BsmArguments = tuple[Literal["c", "p"], float, float, float, float, float, float]
type GreekFunction = Callable[[str, float, float, float, float, float, float], float]
GREEK_FUNCTIONS: dict[GreekMetric, GreekFunction] = {
    "delta": analytical.delta,
    "gamma": analytical.gamma,
    "theta": analytical.theta,
    "vega": analytical.vega,
    "rho": analytical.rho,
}


class PricingInputs(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    right: Literal["CALL", "PUT"]
    spot: float = Field(gt=0, le=1e9)
    strike: float = Field(gt=0, le=1e9)
    years: float = Field(gt=0, le=50)
    risk_free: float = Field(default=0.03, ge=-0.2, le=1)
    dividend_yield: float = Field(default=0, ge=0, le=1)
    volatility: float = Field(gt=0, le=5)


def _args(inputs: PricingInputs) -> BsmArguments:
    return (
        "c" if inputs.right == "CALL" else "p",
        inputs.spot,
        inputs.strike,
        inputs.years,
        inputs.risk_free,
        inputs.volatility,
        inputs.dividend_yield,
    )


def greeks(inputs: PricingInputs, advanced: bool = True) -> dict[str, float | None]:
    arguments = _args(inputs)
    result: dict[str, float] = {
        key: float(function(*arguments)) for key, function in GREEK_FUNCTIONS.items()
    }
    result["theoretical_price"] = float(black_scholes_merton(*arguments))
    if advanced:
        spot_step = max(inputs.spot * 1e-4, 1e-6)
        vol_step = min(1e-3, inputs.volatility / 10)
        time_step = min(1 / 3650, inputs.years / 4)

        def value(metric: GreekMetric, **changes: float) -> float:
            return float(GREEK_FUNCTIONS[metric](*_args(inputs.model_copy(update=changes))))

        plus, minus = inputs.volatility + vol_step, inputs.volatility - vol_step
        result.update(
            {
                "vanna": (value("delta", volatility=plus) - value("delta", volatility=minus))
                / (2 * vol_step),
                "charm": -(
                    value("delta", years=inputs.years + time_step)
                    - value("delta", years=inputs.years - time_step)
                )
                / (2 * time_step * 365),
                "vomma": (value("vega", volatility=plus) - value("vega", volatility=minus))
                / (0.01 * 2 * vol_step),
                "speed": (
                    value("gamma", spot=inputs.spot + spot_step)
                    - value("gamma", spot=inputs.spot - spot_step)
                )
                / (2 * spot_step),
                "color": -(
                    value("gamma", years=inputs.years + time_step)
                    - value("gamma", years=inputs.years - time_step)
                )
                / (2 * time_step * 365),
                "veta": -(
                    value("vega", years=inputs.years + time_step)
                    - value("vega", years=inputs.years - time_step)
                )
                / (0.01 * 2 * time_step * 365),
                "zomma": (value("gamma", volatility=plus) - value("gamma", volatility=minus))
                / (2 * vol_step),
                "ultima": (
                    value("vega", volatility=plus)
                    - 2 * result["vega"]
                    + value("vega", volatility=minus)
                )
                / (0.01 * vol_step**2),
            }
        )
    return {key: value if math.isfinite(value) else None for key, value in result.items()}


def implied_iv(price: float, inputs: PricingInputs) -> float:
    if not math.isfinite(price) or price <= 0:
        raise ValueError("Positive finite option price required for implied volatility")
    lower = max(
        0,
        (
            inputs.spot * math.exp(-inputs.dividend_yield * inputs.years)
            - inputs.strike * math.exp(-inputs.risk_free * inputs.years)
        )
        * (1 if inputs.right == "CALL" else -1),
    )
    upper = (
        inputs.spot * math.exp(-inputs.dividend_yield * inputs.years)
        if inputs.right == "CALL"
        else inputs.strike * math.exp(-inputs.risk_free * inputs.years)
    )
    if not lower < price < upper:
        raise ValueError("Option price lies outside strict European no-arbitrage bounds")
    try:
        iv = float(
            implied_volatility(
                price,
                inputs.spot,
                inputs.strike,
                inputs.years,
                inputs.risk_free,
                inputs.dividend_yield,
                "c" if inputs.right == "CALL" else "p",
            )
        )
    except (ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Implied volatility solver did not converge") from exc
    if not math.isfinite(iv) or not 0 < iv <= 5:
        raise ValueError("Implied volatility is outside the supported 0-500% domain")
    return iv


UNITS = {
    "delta": "underlying units per option unit",
    "gamma": "delta per one spot currency unit",
    "theta": "option currency per calendar day",
    "vega": "option currency per 1 volatility percentage point",
    "rho": "option currency per 1 rate percentage point",
    "vanna": "delta per 1.00 absolute volatility",
    "charm": "delta per calendar day elapsed",
    "vomma": "price per absolute volatility squared",
    "speed": "gamma per spot currency unit",
    "color": "gamma per calendar day elapsed",
    "veta": "price per absolute volatility per calendar day elapsed",
    "zomma": "gamma per absolute volatility",
    "ultima": "price per absolute volatility cubed",
}
