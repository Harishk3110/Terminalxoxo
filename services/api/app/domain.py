from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from statistics import mean, pstdev

Money = Decimal


def decimalize(value: int | float | str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def simple_return(start: Decimal, end: Decimal) -> Decimal:
    if start <= 0:
        raise ValueError("start must be positive")
    return (end - start) / start


def twr_from_returns(returns: list[Decimal]) -> Decimal:
    value = Decimal("1")
    for item in returns:
        value *= Decimal("1") + item
    return value - Decimal("1")


def cagr(start: Decimal, end: Decimal, years: Decimal) -> Decimal:
    if start <= 0 or years <= 0:
        raise ValueError("start and years must be positive")
    return Decimal(str((float(end / start) ** (1 / float(years))) - 1))


def max_drawdown(values: list[Decimal]) -> Decimal:
    if not values:
        return Decimal("0")
    peak = values[0]
    worst = Decimal("0")
    for value in values:
        peak = max(peak, value)
        if peak > 0:
            worst = min(worst, (value - peak) / peak)
    return worst


def annualized_volatility(returns: list[Decimal], periods_per_year: int = 252) -> Decimal:
    if len(returns) < 2:
        return Decimal("0")
    std = pstdev([float(item) for item in returns])
    return Decimal(str(std * math.sqrt(periods_per_year)))


def sharpe_ratio(
    returns: list[Decimal], risk_free_rate: Decimal = Decimal("0"), periods_per_year: int = 252
) -> Decimal:
    if not returns:
        return Decimal("0")
    excess = [float(item - risk_free_rate / Decimal(periods_per_year)) for item in returns]
    std = pstdev(excess)
    if std == 0:
        return Decimal("0")
    return Decimal(str(mean(excess) / std * math.sqrt(periods_per_year)))


def sortino_ratio(
    returns: list[Decimal], target_return: Decimal = Decimal("0"), periods_per_year: int = 252
) -> Decimal:
    downside = [float(item - target_return) for item in returns if item < target_return]
    if not downside:
        return Decimal("0")
    downside_dev = math.sqrt(mean([item * item for item in downside]))
    if downside_dev == 0:
        return Decimal("0")
    return Decimal(
        str(mean([float(item) for item in returns]) / downside_dev * math.sqrt(periods_per_year))
    )


def historical_var(
    returns: list[Decimal], nav: Decimal, confidence: Decimal = Decimal("0.95")
) -> Decimal:
    if not returns:
        return Decimal("0")
    ordered = sorted(returns)
    index = max(0, int((Decimal("1") - confidence) * Decimal(len(ordered))) - 1)
    return quantize_money(ordered[index] * nav)


def historical_cvar(
    returns: list[Decimal], nav: Decimal, confidence: Decimal = Decimal("0.95")
) -> Decimal:
    if not returns:
        return Decimal("0")
    ordered = sorted(returns)
    cutoff = max(1, int((Decimal("1") - confidence) * Decimal(len(ordered))))
    return quantize_money(sum(ordered[:cutoff], Decimal("0")) / Decimal(cutoff) * nav)


def covariance(left: list[Decimal], right: list[Decimal]) -> Decimal:
    n = min(len(left), len(right))
    if n < 2:
        return Decimal("0")
    xs = [float(item) for item in left[-n:]]
    ys = [float(item) for item in right[-n:]]
    mx = mean(xs)
    my = mean(ys)
    return Decimal(str(sum((x - mx) * (y - my) for x, y in zip(xs, ys, strict=False)) / (n - 1)))


def beta(asset_returns: list[Decimal], benchmark_returns: list[Decimal]) -> Decimal:
    var_benchmark = covariance(benchmark_returns, benchmark_returns)
    if var_benchmark == 0:
        return Decimal("0")
    return covariance(asset_returns, benchmark_returns) / var_benchmark


def correlation(left: list[Decimal], right: list[Decimal]) -> Decimal:
    cov = covariance(left, right)
    left_var = covariance(left, left)
    right_var = covariance(right, right)
    if left_var <= 0 or right_var <= 0:
        return Decimal("0")
    return Decimal(str(float(cov) / math.sqrt(float(left_var * right_var))))


def hedge_units(target_notional: Decimal, price: Decimal, multiplier: Decimal) -> Decimal:
    if price <= 0 or multiplier <= 0:
        raise ValueError("price and multiplier must be positive")
    return Decimal(
        int((target_notional / (price * multiplier)).to_integral_value(rounding=ROUND_HALF_UP))
    )


def residual_notional(
    target_notional: Decimal, units: Decimal, price: Decimal, multiplier: Decimal
) -> Decimal:
    return target_notional - units * price * multiplier


@dataclass(frozen=True)
class MovingAverageSignal:
    signal_date: date
    close: Decimal
    fast_average: Decimal
    slow_average: Decimal
    signal: int


def moving_average_signals(
    rows: list[tuple[date, Decimal]], fast: int, slow: int
) -> list[MovingAverageSignal]:
    if fast <= 0 or slow <= 0 or fast >= slow:
        raise ValueError("fast must be positive and less than slow")
    output: list[MovingAverageSignal] = []
    closes = [price for _, price in rows]
    for index in range(slow - 1, len(rows)):
        fast_avg = sum(closes[index - fast + 1 : index + 1], Decimal("0")) / Decimal(fast)
        slow_avg = sum(closes[index - slow + 1 : index + 1], Decimal("0")) / Decimal(slow)
        output.append(
            MovingAverageSignal(
                rows[index][0], rows[index][1], fast_avg, slow_avg, 1 if fast_avg > slow_avg else 0
            )
        )
    return output
