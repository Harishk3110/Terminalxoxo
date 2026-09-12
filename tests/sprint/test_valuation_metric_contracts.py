"""Exact observations, availability and numeric metadata remain distinct."""

from datetime import date
from decimal import Decimal

import pytest
from app.valuation_metrics import metric_summary


def observation() -> dict[str, object]:
    return {
        "date": "2026-01-05",
        "quality": "CALCULATED",
        "return": 0.5,
        "net_return_exact": Decimal("0.000000000000000000000000001"),
        "opening_nav_exact": Decimal("100000"),
        "nav_exact": Decimal("100000.0000000000000000000001"),
        "external_flow_exact": Decimal(0),
        "pnl_exact": Decimal("0.0000000000000000000001"),
        "fee_expense_exact": Decimal(0),
        "benchmark_return_exact": Decimal(0),
    }


def test_exact_return_precedes_rounded_legacy_value() -> None:
    metrics, states, warnings = metric_summary([observation()], date(2026, 1, 5))
    assert metrics["daily"] == 1e-27
    assert states["daily"] == {"state": "AVAILABLE", "reason": None, "observations": 1}
    assert metrics["observations"] == 1
    assert isinstance(metrics["observations"], int)
    assert warnings


def test_explicit_missing_exact_return_does_not_fall_back_to_rounded_value() -> None:
    row = observation()
    row["net_return_exact"] = None
    metrics, states, _ = metric_summary([row], date(2026, 1, 5))
    assert metrics["daily"] is None
    assert metrics["twr"] is None
    assert states["daily"]["state"] == "INSUFFICIENT_DATA"


def test_legacy_return_without_an_exact_field_remains_supported() -> None:
    row = observation()
    del row["net_return_exact"]
    metrics, states, _ = metric_summary([row], date(2026, 1, 5))
    assert metrics["daily"] == 0.5
    assert states["daily"]["state"] == "AVAILABLE"


def test_empty_summary_has_no_fabricated_returns_or_volatility() -> None:
    metrics, states, warnings = metric_summary([], date(2026, 1, 5))
    assert metrics["daily"] is None
    assert metrics["volatility"] is None
    assert metrics["observations"] == 0
    assert metrics["calendar_days"] == 0
    assert states["volatility"]["state"] == "INSUFFICIENT_DATA"
    assert warnings


@pytest.mark.parametrize("value", [True, [], {}, Decimal("NaN"), "Infinity", float("nan")])
def test_invalid_exact_values_do_not_become_financial_observations(value: object) -> None:
    row = observation()
    row["net_return_exact"] = value
    with pytest.raises(ValueError):
        metric_summary([row], date(2026, 1, 5))


@pytest.mark.parametrize("key", ["date", "quality"])
def test_observations_require_string_date_and_quality(key: str) -> None:
    row = observation()
    row[key] = None
    with pytest.raises(ValueError, match="dated quality"):
        metric_summary([row], date(2026, 1, 5))
