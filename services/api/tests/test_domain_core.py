from datetime import date
from decimal import Decimal

from app.domain import (
    annualized_volatility,
    cagr,
    correlation,
    hedge_units,
    historical_cvar,
    historical_var,
    max_drawdown,
    moving_average_signals,
    residual_notional,
    sharpe_ratio,
    sortino_ratio,
    twr_from_returns,
)


def test_performance_calculations():
    returns = [Decimal("0.01"), Decimal("-0.02"), Decimal("0.03")]
    assert twr_from_returns(returns).quantize(Decimal("0.0001")) == Decimal("0.0195")
    assert cagr(Decimal("100"), Decimal("121"), Decimal("2")).quantize(Decimal("0.01")) == Decimal("0.10")
    assert annualized_volatility(returns) > 0
    assert sharpe_ratio(returns) != 0
    assert sortino_ratio(returns) != 0


def test_risk_calculations():
    returns = [Decimal("-0.05"), Decimal("-0.02"), Decimal("0.01"), Decimal("0.03")]
    assert historical_var(returns, Decimal("100000")) < 0
    assert historical_cvar(returns, Decimal("100000")) < 0
    assert max_drawdown([Decimal("100"), Decimal("120"), Decimal("90")]) == Decimal("-0.25")
    assert correlation([Decimal("1"), Decimal("2"), Decimal("3")], [Decimal("1"), Decimal("2"), Decimal("3")]).quantize(Decimal("0.01")) == Decimal("1.00")


def test_hedge_calculations():
    units = hedge_units(Decimal("250000"), Decimal("558.72"), Decimal("1"))
    assert units == Decimal("447")
    assert residual_notional(Decimal("250000"), units, Decimal("558.72"), Decimal("1")) == Decimal("252.16")


def test_moving_average_signal_uses_only_prior_window():
    rows = [(date(2026, 1, idx + 1), Decimal(idx + 1)) for idx in range(28)]
    signals = moving_average_signals(rows, fast=5, slow=20)
    assert signals[0].signal_date == date(2026, 1, 20)
    assert signals[-1].signal == 1
