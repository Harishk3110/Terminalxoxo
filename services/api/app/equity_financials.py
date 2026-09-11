"""Statement frequency, ratios and peer calculations with explicit missing values."""

import math
import re
from collections.abc import Mapping, Sequence
from statistics import mean
from typing import SupportsFloat, TypedDict

import numpy as np
from pydantic import JsonValue, TypeAdapter

STATEMENT_ROWS = TypeAdapter(list[dict[str, JsonValue]])
JSON_VALUE: TypeAdapter[JsonValue] = TypeAdapter(JsonValue)
TEXT_VALUE = TypeAdapter(str)


class ComparableStatistics(TypedDict):
    metric: str
    count: int
    mean: float | None
    median: float | None
    q1: float | None
    q3: float | None
    implied_price: float | None
    outliers: list[str]


FLOW = {
    "revenue",
    "gross_profit",
    "ebit",
    "ebitda",
    "net_income",
    "operating_cash_flow",
    "capex",
    "free_cash_flow",
    "depreciation",
    "interest_expense",
    "tax_expense",
    "dividends",
}
BALANCE = {
    "assets",
    "liabilities",
    "equity",
    "debt",
    "cash",
    "shares",
    "current_assets",
    "current_liabilities",
    "working_capital",
    "invested_capital",
}
METRICS = FLOW | BALANCE


def number(value: object) -> float:
    if not isinstance(value, (str, SupportsFloat)):
        raise ValueError("Financial values must be numeric scalars")
    return float(value)


def divide(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b <= 0:
        return None
    result = a / b
    return result if math.isfinite(result) else None


def quarter_key(period: object) -> int | None:
    match = re.fullmatch(r"(\d{4})[- ]?Q([1-4])", str(period).upper())
    return int(match[1]) * 4 + int(match[2]) - 1 if match else None


def statements(
    data: Mapping[str, object], frequency: str = "ANNUAL", actual_estimate: str = "ACTUAL"
) -> list[dict[str, JsonValue]]:
    rows = [
        row
        for row in STATEMENT_ROWS.validate_python(data["items"], strict=True)
        if row.get("actual_estimate", "ACTUAL") == actual_estimate
    ]
    aliases = {"ANNUAL": {"ANNUAL", "FY", "YEARLY"}, "QUARTERLY": {"QUARTERLY", "QUARTER", "Q"}}
    if frequency != "TTM":
        selected = [row for row in rows if row.get("frequency", "ANNUAL") in aliases[frequency]]
    else:
        quarters = {
            quarter: row
            for row in rows
            if row.get("frequency") in aliases["QUARTERLY"]
            and (quarter := quarter_key(row["year"])) is not None
        }
        selected = []
        for end in sorted(quarters):
            window = [quarters[end - i] for i in reversed(range(4)) if end - i in quarters]
            if len(window) != 4:
                continue
            result: dict[str, JsonValue] = {
                "year": quarters[end]["year"],
                "frequency": "TTM",
                "actual_estimate": actual_estimate,
                "report_date": max(
                    TEXT_VALUE.validate_python(row.get("report_date", ""), strict=True)
                    for row in window
                ),
                "component_periods": [row["year"] for row in window],
            }
            for key in FLOW:
                result[key] = (
                    sum(number(row[key]) for row in window)
                    if all(row.get(key) is not None for row in window)
                    else None
                )
            for key in BALANCE:
                result[key] = quarters[end].get(key)
            result["lineage"] = [row.get("metric_sources", {}) for row in window]
            selected.append(result)
    selected.sort(key=lambda row: str(row["year"]))
    return selected


def ratios(
    row: Mapping[str, object],
    previous: Mapping[str, object] | None = None,
    price: float | None = None,
) -> dict[str, JsonValue]:
    r = {key: number(row[key]) if row.get(key) is not None else None for key in METRICS}
    if r["ebitda"] is None and r["ebit"] is not None and r["depreciation"] is not None:
        r["ebitda"] = r["ebit"] + r["depreciation"]
    if (
        r["free_cash_flow"] is None
        and r["operating_cash_flow"] is not None
        and r["capex"] is not None
    ):
        r["free_cash_flow"] = r["operating_cash_flow"] - abs(r["capex"])
    market_cap = (
        price * r["shares"]
        if price is not None and price > 0 and r["shares"] is not None and r["shares"] > 0
        else None
    )
    enterprise = (
        market_cap + r["debt"] - r["cash"]
        if market_cap is not None and r["debt"] is not None and r["cash"] is not None
        else None
    )
    roe_base = (
        (r["equity"] + number(previous["equity"])) / 2
        if previous and previous.get("equity") is not None and r["equity"] is not None
        else None
    )
    assets_base = (
        (r["assets"] + number(previous["assets"])) / 2
        if previous and previous.get("assets") is not None and r["assets"] is not None
        else None
    )

    def growth(metric: str) -> float | None:
        old = number(previous[metric]) if previous and previous.get(metric) is not None else None
        value = divide(r[metric], old)
        return value - 1 if value is not None else None

    return {
        **r,
        "year": JSON_VALUE.validate_python(row["year"], strict=True),
        "market_cap": market_cap,
        "enterprise_value": enterprise,
        "eps": divide(r["net_income"], r["shares"]),
        "gross_margin": divide(r["gross_profit"], r["revenue"]),
        "ebit_margin": divide(r["ebit"], r["revenue"]),
        "net_margin": divide(r["net_income"], r["revenue"]),
        "fcf_margin": divide(r["free_cash_flow"], r["revenue"]),
        "roe": divide(r["net_income"], roe_base),
        "roa": divide(r["net_income"], assets_base),
        "current_ratio": divide(r["current_assets"], r["current_liabilities"]),
        "debt_to_equity": divide(r["debt"], r["equity"]),
        "revenue_growth": growth("revenue"),
        "earnings_growth": growth("net_income"),
        "pe": divide(market_cap, r["net_income"]),
        "pb": divide(market_cap, r["equity"]),
        "ps": divide(market_cap, r["revenue"]),
        "ev_sales": divide(enterprise, r["revenue"]),
        "ev_ebitda": divide(enterprise, r["ebitda"]),
        "ev_ebit": divide(enterprise, r["ebit"]),
        "fcf_yield": divide(r["free_cash_flow"], market_cap),
        "earnings_yield": divide(r["net_income"], market_cap),
        "dividend_yield": divide(r["dividends"], market_cap),
        "roic": None,
        "forward_pe": None,
        "historical_percentile": None,
    }


def comparable_statistics(
    peers: Sequence[Mapping[str, object]], target: Mapping[str, object]
) -> list[ComparableStatistics]:
    result: list[ComparableStatistics] = []
    for multiple, denominator, ev in (
        ("pe", "net_income", False),
        ("ev_ebitda", "ebitda", True),
        ("ev_sales", "revenue", True),
        ("pb", "equity", False),
    ):
        observed = [(row, number(row[multiple])) for row in peers if row.get(multiple) is not None]
        values = [value for _, value in observed if value > 0]
        if not values:
            result.append(
                {
                    "metric": multiple,
                    "count": 0,
                    "mean": None,
                    "median": None,
                    "q1": None,
                    "q3": None,
                    "implied_price": None,
                    "outliers": [],
                }
            )
            continue
        q1, med, q3 = np.quantile(values, [0.25, 0.5, 0.75])
        fence = 1.5 * (q3 - q1)
        base = number(target[denominator]) if target.get(denominator) is not None else None
        implied = float(med) * base if base is not None and base > 0 else None
        if ev:
            implied = (
                implied - number(target["debt"]) + number(target["cash"])
                if implied is not None
                and target.get("debt") is not None
                and target.get("cash") is not None
                else None
            )
        result.append(
            {
                "metric": multiple,
                "count": len(values),
                "mean": mean(values),
                "median": float(med),
                "q1": float(q1),
                "q3": float(q3),
                "implied_price": divide(
                    implied, number(target["shares"]) if target.get("shares") is not None else None
                ),
                "outliers": [
                    TEXT_VALUE.validate_python(row["symbol"], strict=True)
                    for row, value in observed
                    if value < q1 - fence or value > q3 + fence
                ],
            }
        )
    return result
