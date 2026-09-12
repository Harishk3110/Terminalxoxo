"""Financial JSON retains exact decimals and refuses non-JSON calculation output."""

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from app.portfolio_valuation import jsonable, number


def test_financial_serialization_preserves_exact_values_and_detaches_containers() -> None:
    nested = {"cash": Decimal("-0.00000000000000000000000000017"), "missing": None}
    payload = {
        "positions": [nested],
        "zero": Decimal("0.0000"),
        "flags": (True, False, 0, 0.0),
        "day": date(2026, 1, 7),
        "observed_at": datetime(2026, 1, 7, 12, 30, tzinfo=UTC),
    }
    result = jsonable(payload)
    assert result == {
        "positions": [{"cash": "-1.7E-28", "missing": None}],
        "zero": "0.0000",
        "flags": [True, False, 0, 0.0],
        "day": "2026-01-07",
        "observed_at": "2026-01-07T12:30:00+00:00",
    }
    nested["cash"] = Decimal("3")
    assert result["positions"] == [{"cash": "-1.7E-28", "missing": None}]


@pytest.mark.parametrize(
    "value",
    [
        Decimal("NaN"),
        Decimal("sNaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_serialization_rejects_nested_nonfinite_results(value: Decimal | float) -> None:
    with pytest.raises(ValueError, match="finite"):
        jsonable({"accounting": [{"amount": value}]})


@pytest.mark.parametrize("value", [{1: "not a JSON key"}, {"amounts": {1, 2}}, object()])
def test_serialization_rejects_non_json_values(value: object) -> None:
    with pytest.raises(ValueError):
        jsonable(value)


@pytest.mark.parametrize("value", [Decimal(0), 0, 0.0, "0", Decimal("-0.25"), "1.25"])
def test_numeric_projection_preserves_genuine_zero_and_signed_values(
    value: Decimal | int | float | str,
) -> None:
    assert number(value) == float(value)


@pytest.mark.parametrize("value", [None, Decimal("NaN"), float("nan"), float("inf"), "-Infinity"])
def test_numeric_projection_keeps_unavailable_nonfinite_results_missing(
    value: Decimal | float | str | None,
) -> None:
    assert number(value) is None
