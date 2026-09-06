"""Trade-date economic cash, settlement balances and conservative available cash."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .money import ZERO


@dataclass(frozen=True)
class CashMovement:
    transaction_id: str
    currency: str
    amount: Decimal
    fx: Decimal
    trade_date: date
    settlement_date: date
    account_id: str | None = None
    description: str = "LEDGER"


@dataclass(frozen=True)
class CurrencyCash:
    currency: str
    economic: Decimal
    settled: Decimal
    receivable: Decimal
    payable: Decimal
    available: Decimal
    book_base: Decimal


@dataclass
class PortfolioCashService:
    movements: list[CashMovement] = field(default_factory=list)

    def record(self, movement: CashMovement) -> None:
        if not movement.amount.is_finite() or not movement.fx.is_finite() or movement.fx <= ZERO:
            raise ValueError("Cash amount and FX must be finite, with positive FX")
        if movement.settlement_date < movement.trade_date:
            raise ValueError("Cash settlement cannot precede trade date")
        self.movements.append(movement)

    def balance(self, currency: str, as_of: date, account_id: str | None = None) -> CurrencyCash:
        economic = settled = receivable = payable = book_base = ZERO
        for item in self.movements:
            if item.currency != currency or item.trade_date > as_of:
                continue
            if account_id is not None and item.account_id != account_id:
                continue
            economic += item.amount
            book_base += item.amount * item.fx
            if item.settlement_date <= as_of:
                settled += item.amount
            elif item.amount >= ZERO:
                receivable += item.amount
            else:
                payable -= item.amount
        return CurrencyCash(
            currency, economic, settled, receivable, payable, settled - payable, book_base
        )

    def balances(self, as_of: date, account_id: str | None = None) -> dict[str, CurrencyCash]:
        currencies = {item.currency for item in self.movements if item.trade_date <= as_of}
        return {
            currency: self.balance(currency, as_of, account_id) for currency in sorted(currencies)
        }

    def pending(self, as_of: date) -> list[CashMovement]:
        return [item for item in self.movements if item.trade_date <= as_of < item.settlement_date]

    def settlement_dates(self) -> set[date]:
        return {item.settlement_date for item in self.movements}
