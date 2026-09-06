"""Statement frequency, ratios and peer calculations with explicit missing values."""

import math
import re
from statistics import mean

import numpy as np

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


def divide(a, b):
    if a is None or b is None or b <= 0:
        return None
    result = a / b
    return result if math.isfinite(result) else None


def quarter_key(period):
    match = re.fullmatch(r"(\d{4})[- ]?Q([1-4])", str(period).upper())
    return int(match[1]) * 4 + int(match[2]) - 1 if match else None


def statements(data, frequency="ANNUAL", actual_estimate="ACTUAL"):
    rows = [
        dict(row)
        for row in data["items"]
        if row.get("actual_estimate", "ACTUAL") == actual_estimate
    ]
    aliases = {"ANNUAL": {"ANNUAL", "FY", "YEARLY"}, "QUARTERLY": {"QUARTERLY", "QUARTER", "Q"}}
    if frequency != "TTM":
        selected = [row for row in rows if row.get("frequency", "ANNUAL") in aliases[frequency]]
    else:
        quarters = {
            quarter_key(row["year"]): row
            for row in rows
            if row.get("frequency") in aliases["QUARTERLY"] and quarter_key(row["year"]) is not None
        }
        selected = []
        for end in sorted(quarters):
            window = [quarters.get(end - i) for i in reversed(range(4))]
            if any(row is None for row in window):
                continue
            result = {
                "year": quarters[end]["year"],
                "frequency": "TTM",
                "actual_estimate": actual_estimate,
                "report_date": max(row.get("report_date", "") for row in window),
                "component_periods": [row["year"] for row in window],
            }
            for key in FLOW:
                result[key] = (
                    sum(float(row[key]) for row in window)
                    if all(row.get(key) is not None for row in window)
                    else None
                )
            for key in BALANCE:
                result[key] = quarters[end].get(key)
            result["lineage"] = [row.get("metric_sources", {}) for row in window]
            selected.append(result)
    selected.sort(key=lambda row: str(row["year"]))
    return selected


def ratios(row, previous=None, price=None):
    r = {key: float(row[key]) if row.get(key) is not None else None for key in METRICS}
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
        (r["equity"] + float(previous["equity"])) / 2
        if previous and previous.get("equity") is not None and r["equity"] is not None
        else None
    )
    assets_base = (
        (r["assets"] + float(previous["assets"])) / 2
        if previous and previous.get("assets") is not None and r["assets"] is not None
        else None
    )

    def growth(metric):
        old = float(previous[metric]) if previous and previous.get(metric) is not None else None
        value = divide(r[metric], old)
        return value - 1 if value is not None else None

    return {
        **r,
        "year": row["year"],
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


def comparable_statistics(peers, target):
    result = []
    for multiple, denominator, ev in (
        ("pe", "net_income", False),
        ("ev_ebitda", "ebitda", True),
        ("ev_sales", "revenue", True),
        ("pb", "equity", False),
    ):
        values = [
            row[multiple] for row in peers if row.get(multiple) is not None and row[multiple] > 0
        ]
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
        implied = (
            med * target[denominator]
            if target.get(denominator) is not None and target[denominator] > 0
            else None
        )
        if ev:
            implied = (
                implied - target["debt"] + target["cash"]
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
                "implied_price": divide(implied, target.get("shares")),
                "outliers": [
                    row["symbol"]
                    for row in peers
                    if row.get(multiple) is not None
                    and (row[multiple] < q1 - fence or row[multiple] > q3 + fence)
                ],
            }
        )
    return result
