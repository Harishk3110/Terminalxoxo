"""Persisted financial evidence produced by the offline simulation engine."""

from typing import NotRequired, TypedDict

from pydantic import JsonValue

from .alpha_statistics import AlphaAnalysis


class CurvePoint(TypedDict):
    date: str
    equity: float
    benchmark: float
    drawdown: float
    cash: float


class Fill(TypedDict):
    date: str
    symbol: str
    quantity: float
    price: float
    fee: float


class ClosedTrade(TypedDict):
    symbol: str
    entry: str
    exit: str
    pnl: float
    gross_pnl: float


class RejectedOrder(TypedDict):
    symbol: str
    status: str


class WeightsSnapshot(TypedDict):
    date: str
    weights: dict[str, float]


class Position(TypedDict):
    symbol: str
    quantity: float
    price: float
    weight: float | None


class PositionSnapshot(TypedDict):
    date: str
    positions: list[Position]


DailyReturn = TypedDict("DailyReturn", {"date": str, "return": float})
PeriodReturn = TypedDict("PeriodReturn", {"period": str, "return": float})


class BacktestMetrics(TypedDict):
    total_return: float
    cagr: float | None
    sharpe: float | None
    volatility: float | None
    max_drawdown: float
    trade_count: int
    fill_count: int
    turnover: float
    commission: float
    sortino: float | None
    var_95: float | None
    cvar_95: float | None
    beta: float | None
    tracking_error: float | None
    information_ratio: float | None
    calmar: float | None
    win_rate: float | None
    profit_factor: float | None
    average_win: float | None
    average_loss: float | None
    alpha: float | None
    cost_drag: NotRequired[float]


class SimulationResult(TypedDict):
    equity_curve: list[CurvePoint]
    metrics: BacktestMetrics
    daily_returns: list[DailyReturn]
    monthly_returns: list[PeriodReturn]
    annual_returns: list[PeriodReturn]
    alpha: AlphaAnalysis
    positions: list[PositionSnapshot]
    initial_capital: float
    final_equity: float
    trades: list[ClosedTrade]
    fills: list[Fill]
    rejected_orders: list[RejectedOrder]
    target_weights: list[WeightsSnapshot]
    settings: dict[str, JsonValue]
    calculation_version: str
    warnings: list[str]
