"""Known returns, incomplete calendar bins and valuation precision regressions."""

from dataclasses import replace
from datetime import date
from decimal import Decimal as D

import numpy as np
import pandas as pd
import pytest
from app.performance_domain.contracts import (
    FeeBasis,
    Frequency,
    PerformanceSettings,
    ReturnObservation,
)
from app.performance_domain.metrics import period_returns, rolling_statistics, sample_statistics
from app.performance_domain.money_weighted import money_weighted
from app.performance_domain.series import periods
from app.portfolio_performance import observations_from_snapshot
from app.portfolio_valuation import PortfolioValuationService


def history(count=80):
    days = pd.bdate_range("2026-01-05", periods=count)
    return [
        ReturnObservation(
            day.date(),
            D(str(0.0003 + 0.01 * np.sin(i))),
            D(100),
            D(100),
            D(0),
            D(0),
            D(0),
            D(str(0.005 * np.sin(i))),
        )
        for i, day in enumerate(days)
    ]


def test_capm_and_sample_volatility_match_known_linear_returns():
    rows = history()
    result = sample_statistics(
        periods(rows, Frequency.DAILY, FeeBasis.NET), rows, PerformanceSettings()
    )
    assert result["beta"].value == pytest.approx(2)
    assert result["alpha"].value == pytest.approx(0.0003 * 252)
    assert result["volatility"].value == pytest.approx(
        np.std([float(r.net_return) for r in rows], ddof=1) * np.sqrt(252)
    )
    assert result["upside_capture"].value > 1


@pytest.mark.parametrize("mutation", ["missing", "gap", "weekend", "short"])
def test_invalid_annual_risk_samples_do_not_drop_bad_observations(mutation):
    rows = history()
    if mutation == "missing":
        rows[10] = replace(rows[10], net_return=None)
    elif mutation == "gap":
        rows.pop(10)
    elif mutation == "weekend":
        rows.insert(5, replace(rows[4], day=date(2026, 1, 10)))
    else:
        rows = rows[:59]
    result = sample_statistics(
        periods(rows, Frequency.DAILY, FeeBasis.NET), rows, PerformanceSettings()
    )
    assert all(metric.value is None for metric in result.values())
    assert all(metric.reason for metric in result.values())


def test_missing_benchmark_does_not_hide_portfolio_volatility():
    rows = history()
    rows[10] = replace(rows[10], benchmark_return=None)
    result = sample_statistics(
        periods(rows, Frequency.DAILY, FeeBasis.NET), rows, PerformanceSettings()
    )
    assert result["volatility"].value is not None
    assert result["alpha"].value is None


def test_partial_weekly_bins_not_annualised_as_complete_weeks():
    rows = history(12)[1:]
    chosen = periods(rows, Frequency.WEEKLY, FeeBasis.NET)
    assert [row.statistical_ready for row in chosen] == [False, True, False]
    result = sample_statistics(
        chosen, rows, PerformanceSettings(frequency="WEEKLY", minimum_observations=2)
    )
    assert result["volatility"].value is None
    assert result["volatility"].observations == 1


def test_partial_monthly_bins_keep_returns_but_not_risk_samples():
    rows = history(80)
    chosen = periods(rows, Frequency.MONTHLY, FeeBasis.NET)
    assert chosen[0].value is not None and not chosen[0].statistical_ready
    assert chosen[1].statistical_ready
    assert chosen[2].statistical_ready
    assert not chosen[-1].statistical_ready


def test_rolling_windows_fail_on_gaps_and_recover_with_complete_new_window():
    rows = history(20)
    rows.pop(5)
    result = rolling_statistics(periods(rows, Frequency.DAILY, FeeBasis.NET), 5, 252)
    assert result[4]["volatility"] is not None
    assert result[5]["volatility"] is None
    assert result[-1]["volatility"] is not None


def test_short_history_calendar_returns_are_partial_not_full_year():
    result = period_returns(history(10), PerformanceSettings())
    assert result["ytd"].state == "PARTIAL_PERIOD"
    assert result["mtd"].state == "PARTIAL_PERIOD"
    assert result["cagr"].value is None
    assert result["one_year"].value is None


def test_money_weighted_known_one_year_growth_and_nonconventional_guard():
    rows = [
        ReturnObservation(date(2025, 1, 1), D(0), D(0), D(100), D(100), D(0)),
        ReturnObservation(date(2026, 1, 1), D(".1"), D(100), D(110), D(0), D(10)),
    ]
    result = money_weighted(rows, None, FeeBasis.NET)
    assert result["xirr"].value == pytest.approx(0.1)
    rows.insert(1, ReturnObservation(date(2025, 5, 1), D(0), D(100), D(50), D(-200), D(0)))
    rows[-1] = replace(rows[-1], external_flow=D(500))
    assert money_weighted(rows, None, FeeBasis.NET)["xirr"].value is None


def test_saved_nav_curve_uses_decimal_fields_and_records_fees(ledger_session):
    result = PortfolioValuationService(ledger_session).latest("book", end=date(2026, 1, 9))
    rows = observations_from_snapshot(result)
    assert all(isinstance(row["nav_exact"], str) for row in result["curve"])
    assert all(row.fee_expense == 0 for row in rows)
    assert rows[-1].closing_nav == D("10000")
    assert result["portfolio"]["cash_weight"] == 1
    assert result["metric_metadata"]["ytd"]["state"] == "PARTIAL_PERIOD"


def test_legacy_snapshots_remain_readable_but_gross_fees_are_unavailable():
    result = observations_from_snapshot(
        {
            "curve": [
                {
                    "date": "2026-01-05",
                    "equity": 110,
                    "opening_nav": 100,
                    "return": 0.1,
                    "external_flow": 0,
                    "daily_pnl": 10,
                }
            ]
        }
    )
    assert result[0].net_return == D(".1")
    assert result[0].selected_return(FeeBasis.GROSS)[0] is None
