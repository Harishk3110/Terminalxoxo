"""Geometric period returns and NumPy sample risk statistics with per-metric states."""

import math
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import numpy as np
import pandas as pd

from .contracts import MetricResult, PerformanceSettings, ReturnObservation, ReturnPeriod
from .series import linked, regular_daily_dates


def measured(value: Decimal | float | int | None, count: int, unit: str = "RETURN") -> MetricResult:
    if value is None or not math.isfinite(float(value)):
        return MetricResult.unavailable(count, "Calculation has no finite result", unit)
    return MetricResult(
        str(value) if isinstance(value, Decimal) else value, "AVAILABLE", count, unit=unit
    )


def period_returns(
    observations: Sequence[ReturnObservation],
    settings: PerformanceSettings,
) -> dict[str, MetricResult]:
    if not observations:
        return {
            key: MetricResult.unavailable(0, "No observations in requested range")
            for key in ("twr", "daily", "mtd", "qtd", "ytd", "one_year", "cagr")
        }
    end = observations[-1].day
    starts = {
        "mtd": date(end.year, end.month, 1),
        "qtd": date(end.year, 3 * ((end.month - 1) // 3) + 1, 1),
        "ytd": date(end.year, 1, 1),
        "one_year": (pd.Timestamp(end) - pd.DateOffset(years=1)).date(),
    }
    values = [row.selected_return(settings.fee_basis)[0] for row in observations]
    twr = linked(values)
    result = {"twr": measured(twr, len(values)), "daily": measured(values[-1], 1)}
    for key, start in starts.items():
        selected = [
            value
            for row, value in zip(observations, values, strict=True)
            if row.day >= start and (key != "one_year" or row.day > start)
        ]
        if key == "one_year" and observations[0].day > start:
            result[key] = MetricResult.unavailable(len(selected), "One year of history is required")
        else:
            result[key] = measured(linked(selected), len(selected))
            if result[key].value is not None and observations[0].day > start:
                result[key] = MetricResult(
                    result[key].value,
                    "PARTIAL_PERIOD",
                    len(selected),
                    "History starts after the calendar period boundary",
                )
    days = (end - observations[0].day).days
    if days < 365:
        result["cagr"] = MetricResult.unavailable(len(values), "CAGR requires one year of history")
    elif twr is None or twr <= -1:
        result["cagr"] = MetricResult.unavailable(
            len(values), "CAGR needs a positive linked growth factor"
        )
    else:
        with np.errstate(over="ignore", invalid="ignore"):
            result["cagr"] = measured(float(np.power(float(1 + twr), 365 / days) - 1), len(values))
    return result


def sample_statistics(
    rows: Sequence[ReturnPeriod],
    observations: Sequence[ReturnObservation],
    settings: PerformanceSettings,
) -> dict[str, MetricResult]:
    keys = (
        "volatility",
        "sharpe",
        "sortino",
        "beta",
        "alpha",
        "tracking_error",
        "information_ratio",
        "upside_capture",
        "downside_capture",
    )
    sample = [
        row
        for row in rows
        if row.statistical_ready and (settings.frequency != "DAILY" or row.end.weekday() < 5)
    ]
    count = len(sample)
    reason = None
    if count < settings.minimum_observations:
        reason = f"Requires {settings.minimum_observations} complete {settings.frequency.lower()} observations"
    elif any(row.selected_return(settings.fee_basis)[0] is None for row in observations) or any(
        row.value is None for row in sample
    ):
        reason = "Missing observations cannot be removed from a risk sample"
    elif not regular_daily_dates(observations):
        reason = "Irregular valuation intervals cannot be annualised as daily observations"
    elif any(
        row.day.weekday() >= 5
        and row.selected_return(settings.fee_basis)[0] not in (None, Decimal(0))
        for row in observations
    ):
        reason = "Nonzero weekend returns require an explicit continuous-market calendar"
    if reason:
        return {
            key: MetricResult.unavailable(
                count,
                reason,
                "RATIO" if key in ("sharpe", "sortino", "beta", "information_ratio") else "RETURN",
            )
            for key in keys
        }
    values = np.array([float(row.value) for row in sample if row.value is not None], dtype=float)
    if not np.isfinite(values).all():
        return {
            key: MetricResult.unavailable(count, "Return sample exceeds numerical bounds")
            for key in keys
        }
    annual = settings.periods_per_year
    rf = math.expm1(math.log1p(float(settings.risk_free_rate)) / annual)
    deviation = float(np.std(values, ddof=1))
    excess = values - rf
    downside = float(np.sqrt(np.mean(np.minimum(excess, 0) ** 2)))
    result = {
        key: MetricResult.unavailable(count, "Complete benchmark observations are required")
        for key in keys
    }
    result.update(
        {
            "volatility": measured(deviation * math.sqrt(annual), count),
            "sharpe": measured(
                float(np.mean(excess)) / deviation * math.sqrt(annual) if deviation else None,
                count,
                "RATIO",
            ),
            "sortino": measured(
                float(np.mean(excess)) / downside * math.sqrt(annual) if downside else None,
                count,
                "RATIO",
            ),
        }
    )
    if any(row.benchmark is None for row in sample):
        return result
    benchmark = np.array(
        [float(row.benchmark) for row in sample if row.benchmark is not None], dtype=float
    )
    if not np.isfinite(benchmark).all():
        return result
    variance = float(np.var(benchmark, ddof=1))
    beta = float(np.cov(values, benchmark, ddof=1)[0, 1]) / variance if variance else None
    active = values - benchmark
    tracking = float(np.std(active, ddof=1))
    result.update(
        {
            "beta": measured(beta, count, "RATIO"),
            "alpha": measured(
                (float(np.mean(excess)) - beta * float(np.mean(benchmark - rf))) * annual
                if beta is not None
                else None,
                count,
            ),
            "tracking_error": measured(tracking * math.sqrt(annual), count),
            "information_ratio": measured(
                float(np.mean(active)) / tracking * math.sqrt(annual) if tracking else None,
                count,
                "RATIO",
            ),
        }
    )
    for key, mask in (("upside_capture", benchmark > 0), ("downside_capture", benchmark < 0)):
        selected = int(np.count_nonzero(mask))
        if not selected:
            result[key] = MetricResult.unavailable(0, "No qualifying benchmark periods", "RATIO")
            continue
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            portfolio_growth = float(np.prod(1 + values[mask]))
            benchmark_growth = float(np.prod(1 + benchmark[mask]))
            if portfolio_growth <= 0 or benchmark_growth <= 0:
                result[key] = MetricResult.unavailable(
                    selected, "Capture requires positive growth factors", "RATIO"
                )
                continue
            numerator = math.expm1(math.log(portfolio_growth) / selected)
            denominator = math.expm1(math.log(benchmark_growth) / selected)
            result[key] = measured(
                numerator / denominator if denominator else None, selected, "RATIO"
            )
    return result


def extremes(rows: Sequence[ReturnPeriod], label: str) -> dict[str, MetricResult]:
    keys = (f"{label}_win_rate", f"best_{label}", f"worst_{label}")
    if not rows or any(row.value is None for row in rows):
        return {
            key: MetricResult.unavailable(len(rows), "Complete period returns are required")
            for key in keys
        }
    values = [row.value for row in rows if row.value is not None]
    return {
        keys[0]: measured(sum(value > 0 for value in values) / len(values), len(values)),
        keys[1]: measured(max(values), len(values)),
        keys[2]: measured(min(values), len(values)),
    }


def rolling_statistics(
    rows: Sequence[ReturnPeriod], window: int, annual: int
) -> list[dict[str, object]]:
    if window < 2:
        raise ValueError("Rolling windows require at least two observations")
    rows = [
        row
        for row in rows
        if annual in (12, 52) or row.end.weekday() < 5 or row.value not in (None, Decimal(0))
    ]
    frame = pd.Series([float(row.value) if row.value is not None else np.nan for row in rows])
    deviations = frame.rolling(window, min_periods=window).std(ddof=1) * math.sqrt(annual)
    result = []
    for index, row in enumerate(rows):
        selected = rows[max(0, index + 1 - window) : index + 1]
        complete = len(selected) == window and all(
            item.value is not None and item.statistical_ready for item in selected
        )
        for previous, current in zip(selected, selected[1:], strict=False):
            if annual == 12:
                adjacent = (
                    current.end.year - previous.end.year
                ) * 12 + current.end.month - previous.end.month == 1
            elif annual == 52:
                adjacent = (current.end - previous.end).days == 7
            else:
                adjacent = len(pd.bdate_range(previous.end, current.end, inclusive="right")) == 1
            complete = complete and adjacent
        value = linked([item.value for item in selected]) if complete else None
        result.append(
            {
                "date": row.end,
                "start": selected[0].start,
                "observations": len(selected),
                "window": window,
                "return": value,
                "volatility": float(deviations.iloc[index])
                if complete and np.isfinite(deviations.iloc[index])
                else None,
                "state": "AVAILABLE" if complete else "INSUFFICIENT_DATA",
            }
        )
    return result
