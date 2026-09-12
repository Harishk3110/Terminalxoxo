"""Offline surface consumed by backtest_engine, for Backtrader 1.9.78.123."""

from datetime import date, datetime, tzinfo
from typing import ClassVar, Protocol

from . import feeds as feeds

__version__: str

class _Line(Protocol):
    def __getitem__(self, ago: int) -> float: ...

class _DateLine(_Line, Protocol):
    def date(self, ago: int = 0, tz: tzinfo | None = None) -> date: ...

class DataBase:
    _name: str
    close: _Line
    datetime: _DateLine

class Position:
    size: float

class OrderData:
    dt: float
    size: float
    price: float
    comm: float

class Order:
    Completed: ClassVar[int]
    Canceled: ClassVar[int]
    Margin: ClassVar[int]
    Rejected: ClassVar[int]
    Expired: ClassVar[int]
    ref: int
    status: int
    data: DataBase
    executed: OrderData
    def getstatusname(self, status: int | None = None) -> str: ...

class Trade:
    data: DataBase
    isclosed: bool
    dtopen: float
    dtclose: float
    pnl: float
    pnlcomm: float

class _Broker(Protocol):
    def getvalue(self, datas: list[DataBase] | None = None) -> float: ...
    def getcash(self) -> float: ...
    def setcash(self, cash: float) -> None: ...
    def setcommission(
        self,
        commission: float = 0.0,
        margin: float | None = None,
        mult: float = 1.0,
        commtype: int | None = None,
        percabs: bool = True,
        stocklike: bool = False,
        interest: float = 0.0,
        interest_long: bool = False,
        leverage: float = 1.0,
        automargin: bool | float = False,
        name: str | None = None,
    ) -> None: ...
    def set_slippage_perc(
        self,
        perc: float,
        slip_open: bool = True,
        slip_limit: bool = True,
        slip_match: bool = True,
        slip_out: bool = False,
    ) -> None: ...

class Strategy:
    datas: list[DataBase]
    broker: _Broker
    def __len__(self) -> int: ...
    def getposition(
        self, data: DataBase | None = None, broker: _Broker | None = None
    ) -> Position: ...
    def buy(
        self, data: DataBase | None = None, size: float | None = None, **kwargs: object
    ) -> Order | None: ...
    def sell(
        self, data: DataBase | None = None, size: float | None = None, **kwargs: object
    ) -> Order | None: ...

class Cerebro:
    broker: _Broker
    def __init__(self, *, stdstats: bool = True, maxcpus: int | None = None) -> None: ...
    def adddata(self, data: DataBase, name: str | None = None) -> DataBase: ...
    def addstrategy(self, strategy: type[Strategy], *args: object, **kwargs: object) -> int: ...
    def run(self) -> list[Strategy]: ...

def num2date(x: float, tz: tzinfo | None = None, naive: bool = True) -> datetime: ...
