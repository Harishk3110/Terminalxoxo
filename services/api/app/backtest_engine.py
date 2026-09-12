"""Bounded offline Backtrader simulations. No broker store or live data is attached."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, Self

import backtrader as bt
import numpy as np
import pandas as pd
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, model_validator
from scipy.optimize import minimize

from .backtest_results import (
    BacktestMetrics,
    ClosedTrade,
    CurvePoint,
    Fill,
    PeriodReturn,
    PositionSnapshot,
    RejectedOrder,
    SimulationResult,
    WeightsSnapshot,
)


class BacktestSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    strategy: Literal[
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
    ] = "SMA"
    fast: int = Field(default=20, ge=2, le=250)
    slow: int = Field(default=50, ge=3, le=500)
    capital: float = Field(default=100000, ge=100, le=1e9, allow_inf_nan=False)
    fee_bps: float = Field(default=5, ge=0, le=500, allow_inf_nan=False)
    slippage_bps: float = Field(default=5, ge=0, le=500, allow_inf_nan=False)
    spread_bps: float = Field(default=0, ge=0, le=500, allow_inf_nan=False)
    short_borrow_rate: float = Field(default=0.03, ge=0, le=1, allow_inf_nan=False)
    frequency: Literal["DAILY", "WEEKLY"] = "WEEKLY"
    direction: Literal["LONG_ONLY", "LONG_SHORT"] = "LONG_ONLY"
    weighting: Literal["EQUAL", "SIGNAL", "INVERSE_VOL", "RISK_PARITY"] = "EQUAL"
    gross_limit: float = Field(default=0.95, gt=0, le=1, allow_inf_nan=False)
    position_limit: float = Field(default=0.95, gt=0, le=1, allow_inf_nan=False)
    sector_limit: float = Field(default=1, gt=0, le=1, allow_inf_nan=False)
    minimum_cash: float = Field(default=0.05, ge=0, le=0.95, allow_inf_nan=False)
    top_n: int = Field(default=3, ge=1, le=12)

    @model_validator(mode="after")
    def ordered_windows(self) -> Self:
        if self.fast >= self.slow:
            raise ValueError("Fast window must precede slow window")
        if self.direction == "LONG_SHORT" and (
            self.weighting == "RISK_PARITY" or self.strategy == "RISK_PARITY"
        ):
            raise ValueError("Risk-parity construction currently requires long-only positions")
        return self


def signals_for(
    frames: dict[str, pd.DataFrame], settings: BacktestSettings
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    close = pd.DataFrame({symbol: frame.close for symbol, frame in frames.items()})
    returns = close.pct_change(fill_method=None)
    vol = returns.rolling(settings.slow).std()
    momentum = close.pct_change(settings.slow, fill_method=None)
    strategy = settings.strategy
    if strategy == "SMA":
        signal = close.rolling(settings.fast).mean() / close.rolling(settings.slow).mean() - 1
    elif strategy == "RSI":
        change = close.diff()
        gain = (
            change.clip(lower=0)
            .ewm(alpha=1 / settings.fast, adjust=False, min_periods=settings.fast)
            .mean()
        )
        loss = (
            -change.clip(upper=0)
            .ewm(alpha=1 / settings.fast, adjust=False, min_periods=settings.fast)
            .mean()
        )
        rsi = (
            (100 - 100 / (1 + gain / loss.replace(0, np.nan)))
            .mask((loss == 0) & (gain > 0), 100)
            .mask((gain == 0) & (loss == 0), 50)
        )
        signal = ((30 - rsi).clip(lower=0) - (rsi - 70).clip(lower=0)) / 100
    elif strategy == "MACD":
        macd = (
            close.ewm(span=settings.fast, adjust=False, min_periods=settings.fast).mean()
            - close.ewm(span=settings.slow, adjust=False, min_periods=settings.slow).mean()
        )
        signal = macd - macd.ewm(span=9, adjust=False, min_periods=9).mean()
    elif strategy == "BREAKOUT":
        high = close.rolling(settings.slow).max().shift(1)
        low = close.rolling(settings.slow).min().shift(1)
        signal = (close / high - 1).clip(lower=0) + (close / low - 1).clip(upper=0)
    elif strategy == "MEAN_REVERSION":
        signal = -(close / close.rolling(settings.slow).mean() - 1)
    elif strategy in ("LOW_VOL", "INVERSE_VOL", "RISK_PARITY"):
        signal = 1 / vol.replace(0, np.nan)
    elif strategy == "MULTIFACTOR":
        signal = (momentum.rank(axis=1, pct=True) + (1 / vol).rank(axis=1, pct=True)) / 2 - 0.5
    else:
        signal = momentum
    return signal, returns, vol


def risk_parity(covariance: NDArray[np.float64]) -> NDArray[np.float64]:
    if covariance.ndim != 2 or not len(covariance) or covariance.shape[0] != covariance.shape[1]:
        raise ValueError("Risk parity needs a nonempty square covariance matrix")
    if not np.isfinite(covariance).all() or not np.array_equal(covariance, covariance.T):
        raise ValueError("Risk parity needs a finite symmetric covariance matrix")
    if np.linalg.eigvalsh(covariance).min() < -1e-10:
        raise ValueError("Risk parity needs a positive-semidefinite covariance matrix")
    count = len(covariance)
    if count == 1:
        return np.ones(1)

    def objective(weights: NDArray[np.float64]) -> float:
        contributions = weights * (covariance @ weights)
        total = contributions.sum()
        return float(np.sum((contributions / total - 1 / count) ** 2)) if total > 0 else 1e6

    def budget(weights: NDArray[np.float64]) -> float:
        return float(weights.sum() - 1)

    result = minimize(
        objective,
        np.full(count, 1 / count),
        method="SLSQP",
        bounds=[(1e-6, 1)] * count,
        constraints={"type": "eq", "fun": budget},
        options={"ftol": 1e-10, "maxiter": 200},
    )
    if not result.success:
        raise ValueError("Risk-parity optimisation did not converge")
    return np.asarray(result.x, dtype=np.float64)


def target_weights(
    signal: pd.Series[float],
    volatility: pd.Series[float],
    trailing: pd.DataFrame,
    settings: BacktestSettings,
) -> dict[str, float]:
    valid = signal.dropna()
    if settings.strategy in ("CROSS_SECTIONAL", "LOW_VOL", "MULTIFACTOR"):
        ranked = valid.sort_values(ascending=False, kind="stable")
        positive = ranked.iloc[: settings.top_n]
        negative = (
            ranked.iloc[-settings.top_n :].drop(index=positive.index, errors="ignore")
            if settings.direction == "LONG_SHORT"
            else ranked.iloc[:0]
        )
        valid = pd.concat([positive.abs().clip(lower=1e-8), -negative.abs().clip(lower=1e-8)])
    else:
        valid = valid[valid != 0]
        if settings.direction == "LONG_ONLY":
            valid = valid[valid > 0]
    if valid.empty:
        return {}
    mode = (
        settings.strategy
        if settings.strategy in ("INVERSE_VOL", "RISK_PARITY")
        else settings.weighting
    )
    if mode == "RISK_PARITY":
        sample = trailing[valid.index].dropna()
        if len(sample) < 20:
            return {}
        magnitudes = pd.Series(risk_parity(sample.cov().to_numpy()), index=valid.index)
    elif mode == "INVERSE_VOL":
        magnitudes = 1 / volatility.reindex(valid.index).replace(0, np.nan)
        if magnitudes.isna().any():
            return {}
    elif mode == "SIGNAL":
        magnitudes = valid.abs()
    else:
        magnitudes = pd.Series(1.0, index=valid.index)
    weights = (
        magnitudes
        / magnitudes.sum()
        * min(settings.gross_limit, 1 - settings.minimum_cash)
        * np.sign(valid)
    )
    clipped = weights.clip(-settings.position_limit, settings.position_limit)
    return {str(symbol): float(weight) for symbol, weight in clipped.items()}


def simulate(
    frames: dict[str, pd.DataFrame],
    settings: BacktestSettings,
    external_signals: pd.DataFrame | None = None,
    evaluation_start: pd.Timestamp | None = None,
    sectors: Mapping[str, str | None] | None = None,
) -> SimulationResult:
    if not 1 <= len(frames) <= 12:
        raise ValueError("Select between one and twelve securities")
    first = next(iter(frames.values()))
    if len(first) <= settings.slow + 2 or len(first) > 5000:
        raise ValueError("Require more than slow-window + 2 and at most 5,000 complete daily bars")
    if any(not frame.index.equals(first.index) for frame in frames.values()):
        raise ValueError(
            "All securities require the same complete date grid; missing bars are not filled"
        )
    if settings.strategy == "CROSS_SECTIONAL" and len(frames) < 2:
        raise ValueError("Cross-sectional momentum requires multiple securities")
    if settings.sector_limit < 1 and (
        not sectors or any(not sectors.get(symbol) for symbol in frames)
    ):
        raise ValueError("Sector caps require sector metadata for every security")
    signal, returns, vol = signals_for(frames, settings)
    if external_signals is not None:
        if not external_signals.index.equals(first.index) or list(external_signals.columns) != list(
            frames
        ):
            raise ValueError("External research signals must exactly align with the price grid")
        signal = external_signals
    curve: list[CurvePoint] = []
    fills: list[Fill] = []
    closed: list[ClosedTrade] = []
    rejected: list[RejectedOrder] = []
    snapshots: list[WeightsSnapshot] = []
    positions: list[PositionSnapshot] = []
    benchmark = (
        pd.concat([frame.close / frame.close.iloc[0] for frame in frames.values()], axis=1).mean(
            axis=1
        )
        * settings.capital
    )
    if evaluation_start is not None:
        benchmark = benchmark / benchmark.loc[evaluation_start] * settings.capital

    class ResearchStrategy(bt.Strategy):
        def __init__(self) -> None:
            self.last_week: tuple[int, int] | None = None
            self.peak = settings.capital
            self.pending: list[int] = []

        def next(self) -> None:
            day = pd.Timestamp(self.datas[0].datetime.date(0))
            if evaluation_start is not None and day < evaluation_start:
                return
            nav = float(self.broker.getvalue())
            self.peak = max(self.peak, nav)
            curve.append(
                {
                    "date": day.date().isoformat(),
                    "equity": nav,
                    "benchmark": float(benchmark.loc[day]),
                    "drawdown": nav / self.peak - 1,
                    "cash": float(self.broker.getcash()),
                }
            )
            positions.append(
                {
                    "date": day.date().isoformat(),
                    "positions": [
                        {
                            "symbol": data._name,
                            "quantity": self.getposition(data).size,
                            "price": float(data.close[0]),
                            "weight": self.getposition(data).size * float(data.close[0]) / nav
                            if nav > 0
                            else None,
                        }
                        for data in self.datas
                    ],
                }
            )
            if nav <= 0:
                raise ValueError("Simulation NAV is non-positive")
            calendar = day.isocalendar()
            week = (calendar.year, calendar.week)
            rebalance = settings.frequency == "DAILY" or week != self.last_week
            if (
                len(self) <= settings.slow
                or not rebalance
                or self.pending
                or len(self) == len(first)
            ):
                return
            self.last_week = week
            signal_row, volatility_row = signal.loc[day], vol.loc[day]
            if not isinstance(signal_row, pd.Series) or not isinstance(volatility_row, pd.Series):
                raise ValueError("Research signal dates must identify a unique observation")
            weights = target_weights(
                signal_row, volatility_row, returns.loc[:day].tail(settings.slow), settings
            )
            if sectors and settings.sector_limit < 1:
                totals: dict[str | None, float] = {}
                for symbol, weight in weights.items():
                    sector = sectors[symbol]
                    totals[sector] = totals.get(sector, 0) + abs(weight)
                weights = {
                    symbol: weight * min(1, settings.sector_limit / totals[sectors[symbol]])
                    for symbol, weight in weights.items()
                }
            snapshots.append({"date": day.date().isoformat(), "weights": weights})
            # Reductions are submitted before increases; all market fills occur at the next bar's open.
            targets = [
                (
                    data,
                    int(nav * weights.get(data._name, 0) / data.close[0])
                    - self.getposition(data).size,
                )
                for data in self.datas
            ]
            for data, delta in sorted(targets, key=lambda item: item[1]):
                if delta:
                    order = (
                        self.buy(data=data, size=delta)
                        if delta > 0
                        else self.sell(data=data, size=-delta)
                    )
                    if order is None:
                        raise ValueError("Simulator did not accept a nonzero target order")
                    self.pending.append(order.ref)

        def notify_order(self, order: bt.Order) -> None:
            if order.status in (
                order.Completed,
                order.Canceled,
                order.Margin,
                order.Rejected,
                order.Expired,
            ):
                if order.ref in self.pending:
                    self.pending.remove(order.ref)
                if order.status == order.Completed:
                    fills.append(
                        {
                            "date": bt.num2date(order.executed.dt).date().isoformat(),
                            "symbol": order.data._name,
                            "quantity": float(order.executed.size),
                            "price": float(order.executed.price),
                            "fee": float(order.executed.comm),
                        }
                    )
                elif order.status not in (order.Canceled, order.Expired):
                    rejected.append({"symbol": order.data._name, "status": order.getstatusname()})

        def notify_trade(self, trade: bt.Trade) -> None:
            if trade.isclosed:
                closed.append(
                    {
                        "symbol": trade.data._name,
                        "entry": bt.num2date(trade.dtopen).isoformat(),
                        "exit": bt.num2date(trade.dtclose).isoformat(),
                        "pnl": float(trade.pnlcomm),
                        "gross_pnl": float(trade.pnl),
                    }
                )

    engine = bt.Cerebro(stdstats=False, maxcpus=1)
    engine.broker.setcash(settings.capital)
    engine.broker.setcommission(
        commission=settings.fee_bps / 10000,
        interest=settings.short_borrow_rate,
        stocklike=True,
        percabs=True,
    )
    engine.broker.set_slippage_perc(
        (settings.slippage_bps + settings.spread_bps / 2) / 10000,
        slip_open=True,
        slip_match=True,
        slip_out=True,
    )
    for symbol, frame in frames.items():
        engine.adddata(
            bt.feeds.PandasData(dataname=frame[["open", "high", "low", "close"]]), name=symbol
        )
    engine.addstrategy(ResearchStrategy)
    engine.run()
    equity = pd.Series(
        [row["equity"] for row in curve], index=pd.to_datetime([row["date"] for row in curve])
    )
    realised = equity.pct_change(fill_method=None).iloc[1:]
    years = (equity.index[-1] - equity.index[0]).days / 365.25
    std = float(realised.std())
    turnover = sum(abs(fill["quantity"] * fill["price"]) for fill in fills) / float(equity.mean())
    benchmark_returns = benchmark.reindex(equity.index).pct_change(fill_method=None).iloc[1:]
    excess = realised - benchmark_returns
    downside = float(np.sqrt(np.mean(np.minimum(realised, 0) ** 2)))
    eligible = len(realised) >= 60
    var = float(realised.quantile(0.05)) if eligible else None
    cagr = float((equity.iloc[-1] / settings.capital) ** (1 / years) - 1) if years >= 1 else None
    max_drawdown = min(row["drawdown"] for row in curve)
    wins, losses = (
        [row["pnl"] for row in closed if row["pnl"] > 0],
        [row["pnl"] for row in closed if row["pnl"] < 0],
    )
    from .alpha_statistics import AlphaSettings, alpha_analysis

    alpha = alpha_analysis(
        realised,
        pd.DataFrame({"market_excess": benchmark_returns}),
        AlphaSettings(),
        0,
        benchmark_returns,
    )
    metrics: BacktestMetrics = {
        "total_return": float(equity.iloc[-1] / settings.capital - 1),
        "cagr": cagr,
        "sharpe": float(realised.mean() / std * np.sqrt(252)) if eligible and std > 0 else None,
        "volatility": std * np.sqrt(252) if eligible else None,
        "max_drawdown": max_drawdown,
        "trade_count": len(closed),
        "fill_count": len(fills),
        "turnover": turnover,
        "commission": sum(fill["fee"] for fill in fills),
        "sortino": float(realised.mean() / downside * np.sqrt(252))
        if eligible and downside > 0
        else None,
        "var_95": var,
        "cvar_95": float(realised[realised <= var].mean()) if var is not None else None,
        "beta": float(realised.cov(benchmark_returns) / benchmark_returns.var())
        if eligible and benchmark_returns.var() > 0
        else None,
        "tracking_error": float(excess.std() * np.sqrt(252)) if eligible else None,
        "information_ratio": float(excess.mean() / excess.std() * np.sqrt(252))
        if eligible and excess.std() > 0
        else None,
        "calmar": cagr / abs(max_drawdown) if cagr is not None and max_drawdown < 0 else None,
        "win_rate": len(wins) / len(closed) if closed else None,
        "profit_factor": sum(wins) / abs(sum(losses)) if losses else None,
        "average_win": float(np.mean(wins)) if wins else None,
        "average_loss": float(np.mean(losses)) if losses else None,
        "alpha": alpha["annualised_alpha"],
    }
    return_dates = pd.DatetimeIndex(realised.index)
    monthly: list[PeriodReturn] = [
        {"period": str(period), "return": float(np.prod(1 + group) - 1)}
        for period, group in realised.groupby(return_dates.to_period("M"))
    ]
    annual: list[PeriodReturn] = [
        {"period": str(period), "return": float(np.prod(1 + group) - 1)}
        for period, group in realised.groupby(return_dates.to_period("Y"))
    ]
    return {
        "equity_curve": curve,
        "metrics": metrics,
        "daily_returns": [
            {"date": day.date().isoformat(), "return": float(value)}
            for day, value in zip(return_dates, realised, strict=True)
        ],
        "monthly_returns": monthly,
        "annual_returns": annual,
        "alpha": alpha,
        "positions": positions,
        "initial_capital": settings.capital,
        "final_equity": float(equity.iloc[-1]),
        "trades": closed,
        "fills": fills,
        "rejected_orders": rejected,
        "target_weights": snapshots,
        "settings": settings.model_dump(),
        "calculation_version": "knk-backtest-3.0 / Backtrader 1.9.78.123",
        "warnings": [
            "Offline research simulation only. Completed-close signals fill at the next open; no broker connection or ledger mutation.",
            "Fees, half-spread, slippage and configured short borrowing are modelled. Market impact, taxes, locate availability and stock-specific financing are not.",
            "Unadjusted OHLC requires corporate-action review. Cash earns zero. Open positions remain marked at the final close, not fictitiously liquidated.",
            "Position/gross caps apply to intended close-time weights, not guaranteed next-open exposure after gaps. Integer quantities can leave residual cash.",
            "CAGR needs one year; Sharpe and volatility need 60 daily returns. Risk-free rate is zero. Benchmark is equal-weight buy-and-hold over the selected universe, without trading costs. First/last calendar return bins may be partial.",
            f"Rejected simulated orders: {len(rejected)}. Review cash and gap effects before comparing results.",
        ],
    }
