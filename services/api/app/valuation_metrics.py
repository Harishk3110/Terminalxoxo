"""Project exact ledger returns into metrics and separate availability metadata."""

import math
from collections.abc import Mapping, Sequence
from datetime import date
from decimal import Decimal
from typing import TypedDict

from .performance_domain.contracts import (
    FeeBasis,
    Frequency,
    PerformanceSettings,
    ReturnObservation,
)
from .performance_domain.drawdowns import drawdowns
from .performance_domain.metrics import measured, period_returns, sample_statistics
from .performance_domain.money_weighted import money_weighted
from .performance_domain.series import periods
from .valuation_values import number


class MetricState(TypedDict):
    state: str
    reason: str | None
    observations: int


def _value(row: Mapping[str, object], exact: str, legacy: str) -> Decimal | None:
    item = row.get(exact, row.get(legacy))
    if item is None:
        return None
    if isinstance(item, bool) or not isinstance(item, (Decimal, float, int, str)):
        raise ValueError("Return observations must contain numeric values or null")
    value = Decimal(str(item))
    if not value.is_finite():
        raise ValueError("Return observations must be finite or unavailable")
    return value


def metric_summary(
    curve: Sequence[Mapping[str, object]],
    end: date,
    risk_free: Decimal | float | int | str = 0,
) -> tuple[dict[str, float | None], dict[str, MetricState], list[str]]:
    rows = []
    for row in curve:
        day, quality = row["date"], row["quality"]
        if not isinstance(day, str) or not isinstance(quality, str):
            raise ValueError("Return observations require a dated quality label")
        rows.append(
            ReturnObservation(
                date.fromisoformat(day),
                _value(row, "net_return_exact", "return"),
                _value(row, "opening_nav_exact", "opening_nav"),
                _value(row, "nav_exact", "equity"),
                _value(row, "external_flow_exact", "external_flow"),
                _value(row, "pnl_exact", "daily_pnl"),
                _value(row, "fee_expense_exact", "fee_expense_exact"),
                _value(row, "benchmark_return_exact", "benchmark_return"),
                quality,
            )
        )
    settings = PerformanceSettings(risk_free_rate=Decimal(str(risk_free)))
    daily = periods(rows, Frequency.DAILY, FeeBasis.NET)
    metrics = {
        **period_returns(rows, settings),
        **sample_statistics(daily, rows, settings),
        **money_weighted(rows, None, FeeBasis.NET),
    }
    dd = drawdowns(daily)
    metrics["max_drawdown"] = measured(dd["maximum"], len(rows))
    metrics["current_drawdown"] = measured(dd["current"], len(rows))
    cagr = metrics["cagr"].value
    metrics["calmar"] = measured(
        float(cagr) / abs(float(dd["maximum"])) if cagr is not None and dd["maximum"] else None,
        len(rows),
        "RATIO",
    )
    result = {key: number(metric.value) for key, metric in metrics.items()}
    volatility = result["volatility"]
    result["daily_volatility"] = volatility / math.sqrt(252) if volatility is not None else None
    result["observations"] = sum(row.day.weekday() < 5 for row in rows)
    result["calendar_days"] = (end - rows[0].day).days if rows else 0
    states: dict[str, MetricState] = {
        key: {"state": metric.state, "reason": metric.reason, "observations": metric.observations}
        for key, metric in metrics.items()
    }
    warnings = list(
        dict.fromkeys(
            f"{metric.state}: {metric.reason}" for metric in metrics.values() if metric.reason
        )
    )
    return result, states, warnings
