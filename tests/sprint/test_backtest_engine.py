import numpy as np
import pandas as pd
import pytest
from app.backtest_engine import BacktestSettings, risk_parity, signals_for, simulate


def frames(count=320):
    dates = pd.bdate_range("2024-01-01", periods=count)
    rng = np.random.default_rng(3110)
    result = {}
    for name in ("AAA", "BBB", "CCC"):
        close = 100 * np.exp(np.cumsum(rng.normal(0.0005, 0.015, count)))
        result[name] = pd.DataFrame(
            {"open": close * 0.999, "high": close * 1.02, "low": close * 0.98, "close": close},
            index=dates,
        )
    return result


@pytest.mark.parametrize(
    "strategy",
    [
        "SMA",
        "RSI",
        "MACD",
        "BREAKOUT",
        "MOMENTUM",
        "MEAN_REVERSION",
        "CROSS_SECTIONAL",
        "LOW_VOL",
        "INVERSE_VOL",
        "RISK_PARITY",
        "MULTIFACTOR",
    ],
)
def test_approved_strategy_runs_real_offline_fills(strategy):
    result = simulate(frames(), BacktestSettings(strategy=strategy, fast=5, slow=30, top_n=1))
    assert len(result["equity_curve"]) == 320
    assert result["fills"]
    assert result["metrics"]["fill_count"] == len(result["fills"])
    assert result["final_equity"] == result["equity_curve"][-1]["equity"]
    assert np.isfinite(result["final_equity"])
    assert all(
        sum(abs(weight) for weight in point["weights"].values()) <= 0.950000001
        for point in result["target_weights"]
    )


def test_backtest_is_deterministic_cost_sensitive_and_next_bar() -> None:
    data = frames()
    settings = BacktestSettings(fast=5, slow=30, fee_bps=0, slippage_bps=0)
    result = simulate(data, settings)
    assert result == simulate(data, settings)
    first_fill = result["fills"][0]
    assert first_fill["date"] > result["target_weights"][0]["date"]
    assert first_fill["price"] == pytest.approx(
        data[first_fill["symbol"]].loc[first_fill["date"], "open"]
    )
    costly = simulate(data, settings.model_copy(update={"fee_bps": 50, "slippage_bps": 20}))
    assert costly["final_equity"] != result["final_equity"]
    assert costly["metrics"]["commission"] > 0


def test_future_prices_cannot_change_earlier_signals_or_equity() -> None:
    data = frames()
    settings = BacktestSettings(fast=5, slow=30)
    before = simulate(data, settings)
    changed = {symbol: frame.copy() for symbol, frame in data.items()}
    for frame in changed.values():
        frame.iloc[-20:] *= 2
    after = simulate(changed, settings)
    assert before["equity_curve"][:-20] == after["equity_curve"][:-20]
    pd.testing.assert_frame_equal(
        signals_for(data, settings)[0].iloc[:-20], signals_for(changed, settings)[0].iloc[:-20]
    )


def test_missing_date_grid_rejected_and_short_statistics_null() -> None:
    data = frames(50)
    result = simulate(data, BacktestSettings(fast=5, slow=20))
    assert result["metrics"]["cagr"] is None and result["metrics"]["sharpe"] is None
    data["BBB"] = data["BBB"].iloc[1:]
    with pytest.raises(ValueError, match="date grid"):
        simulate(data, BacktestSettings(fast=5, slow=20))


def test_risk_parity_equalises_diagonal_risk_contributions() -> None:
    covariance = np.diag([0.01, 0.04, 0.09])
    weights = risk_parity(covariance)
    contribution = weights * (covariance @ weights)
    assert contribution / contribution.sum() == pytest.approx([1 / 3] * 3, abs=1e-5)


def test_long_short_includes_signed_positions() -> None:
    result = simulate(
        frames(),
        BacktestSettings(
            strategy="CROSS_SECTIONAL", direction="LONG_SHORT", top_n=1, fast=5, slow=30
        ),
    )
    assert any(
        any(value < 0 for value in row["weights"].values()) for row in result["target_weights"]
    )


def test_cash_and_sector_caps_apply_to_intended_weights() -> None:
    result = simulate(
        frames(),
        BacktestSettings(
            strategy="INVERSE_VOL", slow=30, fast=5, minimum_cash=0.3, sector_limit=0.2
        ),
        sectors={"AAA": "Technology", "BBB": "Technology", "CCC": "Other"},
    )
    for point in result["target_weights"]:
        weights = point["weights"]
        assert sum(abs(weight) for weight in weights.values()) <= 0.70000001
        assert abs(weights.get("AAA", 0)) + abs(weights.get("BBB", 0)) <= 0.20000001
