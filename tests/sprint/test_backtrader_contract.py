"""Verify the narrow typed interface against actual offline Backtrader callbacks."""

from __future__ import annotations

from datetime import date

import backtrader as bt
import pandas as pd
import pytest


def test_real_broker_feed_orders_and_closed_trade_match_the_typed_surface() -> None:
    assert bt.__version__ == "1.9.78.123"
    fills: list[tuple[str, float, float, float]] = []
    closed: list[tuple[float, float]] = []
    observed: list[float] = []

    class Recorder(bt.Strategy):
        def next(self) -> None:
            data = self.datas[0]
            assert isinstance(data, bt.DataBase) and data._name == "FIXTURE"
            assert isinstance(data.datetime.date(0), date)
            assert isinstance(data.close[0], float)
            assert isinstance(self.broker.getvalue(), (int, float))
            assert isinstance(self.broker.getcash(), (int, float))
            observed.append(self.getposition(data).size)
            if len(self) == 1:
                assert self.buy(data=data, size=0) is None
                assert self.buy(data=data, size=2) is not None
            elif len(self) == 3:
                assert self.sell(data=data, size=2) is not None

        def notify_order(self, order: bt.Order) -> None:
            assert isinstance(order, bt.Order)
            assert isinstance(order.ref, int) and isinstance(order.status, int)
            assert isinstance(order.getstatusname(), str)
            for status in (
                order.Completed,
                order.Canceled,
                order.Margin,
                order.Rejected,
                order.Expired,
            ):
                assert isinstance(status, int)
            if order.status == order.Completed:
                assert isinstance(order.executed, bt.OrderData)
                assert order.data._name == "FIXTURE"
                fills.append(
                    (
                        bt.num2date(order.executed.dt).date().isoformat(),
                        order.executed.size,
                        order.executed.price,
                        order.executed.comm,
                    )
                )

        def notify_trade(self, trade: bt.Trade) -> None:
            assert isinstance(trade, bt.Trade) and isinstance(trade.isclosed, bool)
            assert trade.data._name == "FIXTURE"
            if trade.isclosed:
                assert bt.num2date(trade.dtopen).date().isoformat() == "2026-01-02"
                assert bt.num2date(trade.dtclose).date().isoformat() == "2026-01-04"
                closed.append((trade.pnl, trade.pnlcomm))

    data = pd.DataFrame(
        {key: [100.0, 101.0, 102.0, 103.0, 104.0] for key in ("open", "high", "low", "close")},
        index=pd.date_range("2026-01-01", periods=5),
    )
    engine = bt.Cerebro(stdstats=False, maxcpus=1)
    engine.broker.setcash(1000)
    engine.broker.setcommission(commission=0.001, interest=0.03, stocklike=True, percabs=True)
    engine.broker.set_slippage_perc(0, slip_open=True, slip_match=True, slip_out=True)
    feed = bt.feeds.PandasData(dataname=data)
    assert engine.adddata(feed, name="FIXTURE") is feed
    assert isinstance(engine.addstrategy(Recorder), int)
    strategies = engine.run()
    assert len(strategies) == 1 and isinstance(strategies[0], Recorder)
    assert observed == [0, 2, 2, 0, 0]
    assert fills == [
        ("2026-01-02", 2, 101.0, 2 * 101.0 * 0.001),
        ("2026-01-04", -2, 103.0, 2 * 103.0 * 0.001),
    ]
    assert len(closed) == 1
    assert closed[0] == pytest.approx((4, 3.592), abs=1e-12)
    assert engine.broker.getvalue() == pytest.approx(1003.592, abs=1e-12)
    assert engine.broker.getcash() == pytest.approx(1003.592, abs=1e-12)
