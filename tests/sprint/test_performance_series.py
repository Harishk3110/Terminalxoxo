"""Return periods retain missing data and preserve compounding across calendar groups."""

from datetime import date, timedelta
from decimal import Decimal as D

import pytest
from app.performance_domain.contracts import (
    FeeBasis,
    Frequency,
    PerformanceSettings,
    ReturnObservation,
)
from app.performance_domain.series import (
    linked,
    periods,
    regular_daily_dates,
    select_observations,
    series_payload,
)
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError


def point(day: int, value: str | None = "0.1", **kwargs) -> ReturnObservation:
    return ReturnObservation(
        date(2026, 1, day),
        D(value) if value is not None else None,
        D(100),
        D(110),
        D(0),
        D(10),
        **kwargs,
    )


def test_geometric_linking_is_not_the_sum_of_returns() -> None:
    assert linked([D("0.1"), D("-0.1")]) == D("-0.01")
    assert linked([]) is None
    assert linked([None, D("0.1")]) is None
    assert linked([D("-1"), D("0.5")]) == -1
    assert linked([D("-1.01")]) is None


def test_aggregation_preserves_all_monthly_observations_and_actual_dates() -> None:
    rows = [point(5), point(6, "-0.1"), point(30, "0")]
    monthly = periods(rows, Frequency.MONTHLY, FeeBasis.NET)
    assert len(monthly) == 1
    assert monthly[0].value == D("-0.01")
    assert monthly[0].start == date(2026, 1, 5)
    assert monthly[0].end == date(2026, 1, 30)
    assert monthly[0].observations == 3
    assert monthly[0].missing == 0
    assert monthly[0].benchmark is None


def test_weekly_groups_are_friday_ended_and_do_not_drop_weekend_observations() -> None:
    rows = [point(9), point(10), point(12)]
    grouped = periods(rows, Frequency.WEEKLY, FeeBasis.NET)
    assert [row.observations for row in grouped] == [1, 2]
    assert grouped[1].value == D("0.21")
    assert grouped[1].start == date(2026, 1, 10)


def test_missing_observation_invalidates_its_period_and_subsequent_cumulative_index() -> None:
    rows = periods([point(5), point(6, None), point(7)], Frequency.DAILY, FeeBasis.NET)
    payload = series_payload(rows)
    assert payload[0]["return_index"] == D("1.1")
    assert payload[1]["state"] == "INCOMPLETE"
    assert payload[1]["missing"] == 1
    assert payload[1]["return_index"] is None
    assert payload[2]["value"] == D("0.1")
    assert payload[2]["return_index"] is None
    month = periods([point(5), point(6, None)], Frequency.MONTHLY, FeeBasis.NET)[0]
    assert month.value is None
    assert month.missing == 1
    assert "Missing" in month.reason


def test_gross_returns_use_recorded_fee_expense_and_bod_external_capital() -> None:
    row = ReturnObservation(date(2026, 1, 5), D("0.09"), D(100), D(218), D(100), D(18), D(2))
    assert row.selected_return(FeeBasis.NET) == (D("0.09"), None)
    assert row.selected_return(FeeBasis.GROSS) == (D("0.10"), None)
    assert point(5).selected_return(FeeBasis.GROSS)[0] is None
    assert "not recorded" in point(5).selected_return(FeeBasis.GROSS)[1]


def test_invalid_capital_and_returns_do_not_become_gross_zero() -> None:
    row = ReturnObservation(date(2026, 1, 5), D(0), D(0), D(0), D(0), D(0), D(1))
    assert row.selected_return(FeeBasis.GROSS)[0] is None
    assert point(5, "-1.1").selected_return(FeeBasis.NET)[0] is None


@pytest.mark.parametrize(
    "field",
    [
        "net_return",
        "opening_nav",
        "closing_nav",
        "external_flow",
        "daily_pnl",
        "fee_expense",
        "benchmark_return",
    ],
)
@pytest.mark.parametrize("value", [D("NaN"), D("Infinity"), 1.1])
def test_observation_contract_rejects_non_decimal_or_non_finite_values(field, value) -> None:
    values = {
        "day": date(2026, 1, 5),
        "net_return": D(0),
        "opening_nav": D(1),
        "closing_nav": D(1),
        "external_flow": D(0),
        "daily_pnl": D(0),
        field: value,
    }
    with pytest.raises(ValueError, match=field):
        ReturnObservation(**values)


def test_selection_is_inclusive_and_does_not_sort_or_deduplicate_bad_history() -> None:
    rows = [point(5), point(6), point(7)]
    assert select_observations(rows, date(2026, 1, 6), date(2026, 1, 6)) == [rows[1]]
    assert select_observations(rows, date(2026, 2, 1), None) == []
    for invalid in ([rows[0], rows[0]], list(reversed(rows))):
        with pytest.raises(ValueError, match="unique ascending"):
            select_observations(invalid, None, None)
    with pytest.raises(ValueError, match="must not follow"):
        select_observations(rows, date(2026, 2, 1), date(2026, 1, 1))


def test_business_calendar_flags_unobserved_weekdays_but_not_a_normal_weekend() -> None:
    assert regular_daily_dates([point(9), point(12)])
    assert not regular_daily_dates([point(5), point(9)])
    assert regular_daily_dates([])


@pytest.mark.parametrize(
    "settings",
    [
        {"risk_free_rate": "NaN"},
        {"risk_free_rate": "-1"},
        {"risk_free_rate": "1.1"},
        {"trading_days": 199},
        {"trading_days": 367},
        {"trading_days": True},
        {"minimum_observations": 1},
        {"rolling_window": 1},
        {"frequency": "QUARTERLY"},
        {"fee_basis": "INVENTED"},
        {"unknown": 123},
        {"start": "2026-02-01", "end": "2026-01-01"},
    ],
)
def test_settings_enforce_explicit_supported_conventions(settings) -> None:
    with pytest.raises(ValidationError):
        PerformanceSettings(**settings)


@given(
    st.lists(
        st.decimals(
            min_value="-0.4", max_value="0.4", places=6, allow_nan=False, allow_infinity=False
        ),
        min_size=1,
        max_size=25,
    )
)
def test_monthly_grouping_preserves_total_geometric_return(values) -> None:
    rows = [
        ReturnObservation(
            date(2026, 1, 20) + timedelta(days=index), value, D(100), D(100), D(0), D(0)
        )
        for index, value in enumerate(values)
    ]
    monthly = periods(rows, Frequency.MONTHLY, FeeBasis.NET)
    assert abs(linked([row.value for row in monthly]) - linked(values)) < D("1e-27")
