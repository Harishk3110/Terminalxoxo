"""Offline Pine templates and comparisons against user-supplied TradingView exports."""

import csv
import hashlib
import io
from datetime import date
from typing import Literal, Self

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .backtest_engine import BacktestSettings, signals_for
from .pine_results import PineComparison, PineStrategy, PineTemplate, SignalComparison


class PineSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    strategy: PineStrategy = "SMA"
    fast: int = Field(default=20, ge=2, le=250)
    slow: int = Field(default=50, ge=3, le=500)
    direction: Literal["LONG_ONLY", "LONG_SHORT"] = "LONG_ONLY"
    commission_pct: float = Field(default=0.05, ge=0, le=5)
    slippage_ticks: int = Field(default=1, ge=0, le=1000)
    allocation_pct: float = Field(default=95, gt=0, le=100)
    start: date = date(2020, 1, 1)
    end: date = date(2030, 1, 1)
    session: str = Field(
        default="0000-0000", pattern=r"^([01]\d|2[0-3])[0-5]\d-([01]\d|2[0-3])[0-5]\d$"
    )
    stop_pct: float = Field(default=0, ge=0, le=50)
    profit_pct: float = Field(default=0, ge=0, le=1000)
    trailing_ticks: int = Field(default=0, ge=0, le=100000)
    activation_ticks: int = Field(default=1, ge=1, le=100000)

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if self.fast >= self.slow or self.end <= self.start:
            raise ValueError("Fast must precede slow; end must follow start")
        if self.start.year < 1970 or self.end.year > 2100:
            raise ValueError("Dates must be between 1970 and 2100")
        if self.stop_pct and self.trailing_ticks:
            raise ValueError("Choose a fixed stop or a trailing stop, not both")
        return self


def generate(settings: PineSettings) -> PineTemplate:
    formulas = {
        "SMA": "fast = ta.sma(close, fastLength)\nslow = ta.sma(close, slowLength)\nrawSignal = fast / slow - 1",
        "RSI": "rsi = ta.rsi(close, fastLength)\nrawSignal = (math.max(30 - rsi, 0) - math.max(rsi - 70, 0)) / 100",
        "MACD": "[macd, signalLine, histogram] = ta.macd(close, fastLength, slowLength, 9)\nrawSignal = histogram",
        "BREAKOUT": "priorHigh = ta.highest(close, slowLength)[1]\npriorLow = ta.lowest(close, slowLength)[1]\nrawSignal = math.max(close / priorHigh - 1, 0) + math.min(close / priorLow - 1, 0)",
    }
    source = f'''//@version=6
// KnK research simulation. No broker connection or webhook execution.
strategy("KnK {settings.strategy}", overlay=true, pyramiding=0, initial_capital=100000, currency=currency.SGD, default_qty_type=strategy.percent_of_equity, default_qty_value={settings.allocation_pct}, commission_type=strategy.commission.percent, commission_value={settings.commission_pct}, slippage={settings.slippage_ticks}, process_orders_on_close=false, calc_on_every_tick=false, margin_long=100, margin_short=100)
fastLength = input.int({settings.fast}, "Fast window", minval=2, maxval=250)
slowLength = input.int({settings.slow}, "Slow window", minval=3, maxval=500)
startTime = input.time(timestamp("{settings.start.isoformat()}T00:00:00+0000"), "Start UTC")
endTime = input.time(timestamp("{settings.end.isoformat()}T00:00:00+0000"), "End UTC (exclusive)")
tradeSession = input.session("{settings.session}", "Entry session (exchange timezone)")
allowShort = input.bool({str(settings.direction == "LONG_SHORT").lower()}, "Allow simulated shorts")
stopPct = input.float({settings.stop_pct}, "Fixed stop %", minval=0, maxval=50) / 100
profitPct = input.float({settings.profit_pct}, "Profit target %", minval=0, maxval=1000) / 100
trailTicks = input.int({settings.trailing_ticks}, "Trailing offset ticks", minval=0, maxval=100000)
activationTicks = input.int({settings.activation_ticks}, "Trailing activation ticks", minval=1, maxval=100000)
if fastLength >= slowLength or endTime <= startTime or (stopPct > 0 and trailTicks > 0)
    runtime.error("Invalid windows, dates, or conflicting stops")
{formulas[settings.strategy]}
rawDirection = na(rawSignal) ? na : rawSignal > 0 ? 1 : rawSignal < 0 ? -1 : 0
entryWindow = time >= startTime and time < endTime and not na(time(timeframe.period, tradeSession))
if barstate.isconfirmed and not na(rawDirection)
    if time >= endTime
        strategy.cancel_all()
        strategy.close_all(comment="End date")
    else if entryWindow
        if rawDirection > 0 and strategy.position_size <= 0
            strategy.entry("Long", strategy.long, alert_message="KnK research LONG")
            alert("KnK research LONG", alert.freq_once_per_bar_close)
        else if rawDirection < 0 and allowShort and strategy.position_size >= 0
            strategy.entry("Short", strategy.short, alert_message="KnK research SHORT")
            alert("KnK research SHORT", alert.freq_once_per_bar_close)
        else if rawDirection == 0 or (rawDirection < 0 and not allowShort)
            strategy.close_all(comment="Flat signal")
    if strategy.position_size != 0 and (stopPct > 0 or profitPct > 0 or trailTicks > 0)
        side = strategy.position_size > 0 ? 1 : -1
        stopPrice = stopPct > 0 ? strategy.position_avg_price * (1 - side * stopPct) : na
        profitPrice = profitPct > 0 ? strategy.position_avg_price * (1 + side * profitPct) : na
        strategy.exit("Protection", stop=stopPrice, limit=profitPrice, trail_points=trailTicks > 0 ? activationTicks : na, trail_offset=trailTicks > 0 ? trailTicks : na)
plot(rawDirection, "KNK_SIGNAL", display=display.data_window)
'''
    return {
        "source": source,
        "source_hash": hashlib.sha256(source.encode()).hexdigest(),
        "settings": settings.model_dump(mode="json"),
        "version": "knk-pine-2.0",
        "language": "Pine Script v6",
        "compatibility": "PARTIALLY_SUPPORTED",
        "compilation": "UNVERIFIED",
        "comparison": "NOT_COMPARED",
        "quality": "RESEARCH TEMPLATE",
        "as_of": None,
        "warnings": [
            "Manual TradingView compilation is required; no compiler or broker is connected.",
            "KNK_SIGNAL is raw indicator direction, not fills or portfolio weights. Entry sessions use exchange timezone; date boundaries use UTC. Existing positions are not liquidated at session end.",
            "Next-open simulation. Protective orders are first submitted at the close after an entry fill. Overnight gaps, fill paths and TradingView currency conversion may differ from KnK backtests.",
            "RSI uses TradingView Wilder initialization; KnK uses pandas EWM initialization. MACD warm-up histories may differ. Compare identical bars and unchanged settings.",
            "Breakout uses prior closing-price extrema, not intrabar high/low. No pyramiding; RSI and breakout flatten on neutral signals. This is not arbitrary Python-to-Pine conversion.",
        ],
    }


def compare_export(raw: bytes, settings: PineSettings) -> PineComparison:
    if len(raw) > 10_000_000:
        raise ValueError("Signal export exceeds 10 MB")
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    columns = reader.fieldnames or []
    if len(columns) != len(set(columns)) or not {"time", "close", "KNK_SIGNAL"}.issubset(columns):
        raise ValueError("CSV needs unique time, close and KNK_SIGNAL columns")
    rows = []
    for index, row in enumerate(reader):
        if index >= 50000:
            raise ValueError("Signal export exceeds 50,000 bars")
        if None in row or any(row[key] is None for key in ("time", "close", "KNK_SIGNAL")):
            raise ValueError("CSV row does not match the header")
        value = row["time"]
        stamp = (
            pd.to_datetime(int(value), unit="s", utc=True)
            if value.isdigit()
            else pd.Timestamp(value)
        )
        if stamp.tzinfo is None:
            raise ValueError("Timestamps need an explicit timezone or Unix seconds")
        close = float(row["close"])
        direction = None if row["KNK_SIGNAL"] in ("", "NaN", "na") else float(row["KNK_SIGNAL"])
        if not np.isfinite(close) or close <= 0 or direction not in (None, -1, 0, 1):
            raise ValueError(f"Invalid close or directional signal at row {index + 2}")
        rows.append({"time": stamp.tz_convert("UTC"), "close": close, "signal": direction})
    if len(rows) < settings.slow + 10:
        raise ValueError("More bars are required for slow-window and MACD warm-up")
    frame = pd.DataFrame(rows).set_index("time")
    if frame.index.has_duplicates or not frame.index.is_monotonic_increasing:
        raise ValueError("Bars must be unique and strictly chronological")
    signal, _, _ = signals_for(
        {"EXPORT": frame},
        BacktestSettings(strategy=settings.strategy, fast=settings.fast, slow=settings.slow),
    )
    compared: list[SignalComparison] = []
    mismatches: list[SignalComparison] = []
    missing, warmup = 0, 0
    directions: pd.Series[float] = signal["EXPORT"]
    observed_directions: pd.Series[float] = frame["signal"]
    closes: pd.Series[float] = frame["close"]
    for comparison_stamp, raw_signal in directions.items():
        if not isinstance(comparison_stamp, pd.Timestamp):
            raise ValueError("Signal comparison requires timestamp-indexed bars")
        if pd.isna(raw_signal):
            warmup += 1
            continue
        observed = observed_directions.at[comparison_stamp]
        if pd.isna(observed):
            missing += 1
            continue
        expected = int(np.sign(raw_signal))
        item: SignalComparison = {
            "time": comparison_stamp.isoformat(),
            "close": float(closes.at[comparison_stamp]),
            "knk": expected,
            "tradingview": int(observed),
            "match": bool(expected == observed),
        }
        compared.append(item)
        if not item["match"]:
            mismatches.append(item)
    if not compared:
        raise ValueError("No comparable post-warm-up signals")
    return {
        "state": "MISMATCHES" if mismatches else "MATCHED_OBSERVED_BARS",
        "source": "USER_TRADINGVIEW_CSV / KnK Backtest signals_for",
        "quality": "USER PROVIDED / UNVERIFIED EXTERNAL EXPORT",
        "as_of": pd.Timestamp(frame.index[-1]).isoformat(),
        "source_hash": hashlib.sha256(raw).hexdigest(),
        "row_count": len(rows),
        "compared": len(compared),
        "warmup_excluded": warmup,
        "missing_signals": missing,
        "mismatch_count": len(mismatches),
        "match_rate": 1 - len(mismatches) / len(compared),
        "mismatches": mismatches[:500],
        "items": compared[:500],
        "warnings": [
            "Signal direction only, recomputed on supplied closing bars. No independent price verification, fill, fee, stop, session, portfolio-weight or P&L equivalence is established.",
            "Match rate excludes warm-up and missing signals; inspect coverage. At most 500 detail rows are returned; counts use the entire file.",
            "RSI initialization and MACD warm-up can differ. User must confirm the TradingView template inputs and chart settings match the saved template.",
        ],
    }
