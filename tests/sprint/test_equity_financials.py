from copy import deepcopy
from decimal import Decimal
from fractions import Fraction

import numpy as np
import pytest
from app.equity_financials import comparable_statistics, divide, number, ratios, statements
from pydantic import JsonValue, ValidationError


def test_ttm_needs_consecutive_quarters_and_keeps_point_in_time_balances() -> None:
    data = {
        "items": [
            {
                "year": f"2025Q{i}",
                "frequency": "QUARTERLY",
                "revenue": 10 * i,
                "cash": 5 * i,
                "shares": 10,
                "report_date": f"2025-0{i + 1}-01",
            }
            for i in range(1, 5)
        ]
    }
    rows = statements(data, "TTM")
    assert len(rows) == 1 and rows[0]["revenue"] == 100 and rows[0]["cash"] == 20
    assert rows[0]["net_income"] is None and rows[0]["shares"] == 10
    data["items"][1]["actual_estimate"] = "ESTIMATE"
    assert statements(data, "TTM") == []


def test_ratios_missing_negative_denominators_and_average_balances() -> None:
    row = {
        "year": "2025",
        "revenue": 100,
        "net_income": -5,
        "shares": 10,
        "equity": 50,
        "ebit": 10,
        "depreciation": 3,
        "operating_cash_flow": 20,
        "capex": -5,
        "debt": 20,
        "cash": 5,
    }
    result = ratios(row, {"equity": 30, "revenue": 80}, 10)
    assert result["pe"] is None
    assert result["ebitda"] == 13
    assert result["fcf_yield"] == 0.15
    assert result["roe"] == -0.125
    assert result["revenue_growth"] == 0.25
    assert result["ev_sales"] == 1.15
    assert result["forward_pe"] is None


def test_comps_exclude_missing_multiples_and_translate_ev_to_equity() -> None:
    peers = [
        {"symbol": str(i), "ev_sales": value} for i, value in enumerate([1, 2, 3, 4, 100, None])
    ]
    target = {"revenue": 100, "debt": 20, "cash": 10, "shares": 10}
    row = next(row for row in comparable_statistics(peers, target) if row["metric"] == "ev_sales")
    assert row["count"] == 5 and row["median"] == 3
    assert row["implied_price"] == 29
    assert row["outliers"] == ["4"]
    assert comparable_statistics([], target)[0]["median"] is None


@pytest.mark.parametrize("value", [0, -0.0, "12.5", Decimal("12.5")])
def test_numeric_statement_boundary_accepts_existing_scalar_inputs(value: object) -> None:
    assert number(value) == float(str(value))


@pytest.mark.parametrize("value", [None, [], {"value": 12}, object()])
def test_compound_statement_metrics_are_not_coerced_to_numbers(value: object) -> None:
    with pytest.raises(ValueError, match="numeric scalars"):
        number(value)


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        np.bool_(True),
        float("nan"),
        float("inf"),
        float("-inf"),
        "NaN",
        "Infinity",
        "-Infinity",
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        np.float32("inf"),
        10**400,
    ],
)
def test_financial_numbers_reject_boolean_nonfinite_and_overflow_inputs(value: object) -> None:
    with pytest.raises(ValueError, match="numeric|finite"):
        number(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-0.0, -0.0),
        ("-0", -0.0),
        (np.float32(0.1), float(np.float32(0.1))),
        (Decimal("1.234567890123456789"), float(Decimal("1.234567890123456789"))),
        (Fraction(1, 3), 1 / 3),
        (-123.5, -123.5),
    ],
)
def test_financial_number_conversion_preserves_existing_bits(
    value: object, expected: float
) -> None:
    assert number(value).hex() == expected.hex()


def test_financial_number_retains_the_existing_float_protocol() -> None:
    class MetricScalar:
        def __float__(self) -> float:
            return 12.5

    assert number(MetricScalar()) == 12.5


@pytest.mark.parametrize("boundary", ["current", "previous", "price"])
@pytest.mark.parametrize("value", [True, float("nan"), float("inf"), float("-inf")])
def test_ratio_inputs_reject_invalid_current_previous_and_price_values(
    boundary: str, value: float
) -> None:
    current: dict[str, object] = {"year": "2025", "revenue": 100, "shares": 10}
    previous: dict[str, object] = {"year": "2024", "revenue": 80}
    if boundary == "current":
        current["revenue"] = value
    elif boundary == "previous":
        previous["revenue"] = value
    with pytest.raises(ValueError, match="numeric|finite"):
        ratios(current, previous, value if boundary == "price" else 10)


@pytest.mark.parametrize("denominator", [None, 0, -1])
def test_unavailable_ratio_denominators_do_not_become_zero(denominator: float | None) -> None:
    assert divide(10, denominator) is None
    assert divide(None, 10) is None
    assert divide(0, 10) == 0


def test_ttm_preserves_lineage_and_does_not_mutate_input() -> None:
    items: list[dict[str, JsonValue]] = [
        {
            "year": f"2025Q{i}",
            "frequency": "Q",
            "revenue": str(i),
            "cash": i,
            "report_date": f"2025-{i + 1:02}-01",
            "metric_sources": {"revenue": {"dataset_version_id": str(i)}},
        }
        for i in range(1, 5)
    ]
    before = deepcopy(items)
    result = statements({"items": items}, "TTM")
    assert result[0]["revenue"] == 10
    assert result[0]["cash"] == 4
    assert result[0]["report_date"] == "2025-05-01"
    assert result[0]["component_periods"] == [f"2025Q{i}" for i in range(1, 5)]
    assert result[0]["lineage"] == [item["metric_sources"] for item in items]
    assert items == before
    result[0]["revenue"] = 100
    assert items == before


@pytest.mark.parametrize("items", [None, "not rows", [42], [{42: "not a column"}]])
def test_statement_input_requires_named_json_rows(items: object) -> None:
    with pytest.raises(ValidationError):
        statements({"items": items})
