"""Transaction, policy and auditable lot records shared by accounting services."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from .money import ONE, ZERO, decimal


class CostMethod(StrEnum):
    AVERAGE = "AVERAGE"
    FIFO = "FIFO"


class Direction(StrEnum):
    LONG = "LONG"
    SHORT = "SHORT"


class TransactionKind(StrEnum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"
    DIVIDEND = "DIVIDEND"
    INTEREST = "INTEREST"
    COMMISSION = "COMMISSION"
    FEE = "FEE"
    TAX = "TAX"
    FX_CONVERSION = "FX_CONVERSION"
    SPLIT = "SPLIT"
    REVERSE_SPLIT = "REVERSE_SPLIT"
    SPINOFF = "SPINOFF"
    MERGER = "MERGER"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    OTHER_ADJUSTMENT = "OTHER_ADJUSTMENT"


TRANSACTION_TYPES = {kind.value for kind in TransactionKind}
SECURITY_MOVEMENTS = {"BUY", "SELL", "SHORT", "COVER", "TRANSFER_IN", "TRANSFER_OUT"}


@dataclass(frozen=True)
class AccountingPolicy:
    method: CostMethod = CostMethod.AVERAGE
    capitalize_commissions: bool = False
    capitalize_fees: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.method, CostMethod):
            raise ValueError("Cost method must be AVERAGE or FIFO")
        if not isinstance(self.capitalize_commissions, bool) or not isinstance(
            self.capitalize_fees, bool
        ):
            raise ValueError("Cost treatment switches must be boolean")

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> AccountingPolicy:
        raw = config.get("accounting", {})
        if not isinstance(raw, dict):
            raise ValueError("Accounting policy must be an object")
        method = CostMethod(str(raw.get("method", "AVERAGE")).upper())
        commissions = raw.get("capitalize_commissions", False)
        fees = raw.get("capitalize_fees", False)
        if not isinstance(commissions, bool) or not isinstance(fees, bool):
            raise ValueError("Cost treatment switches must be boolean")
        return cls(method, commissions, fees)

    def to_dict(self) -> dict[str, str | bool]:
        return {
            "method": self.method.value,
            "capitalize_commissions": self.capitalize_commissions,
            "capitalize_fees": self.capitalize_fees,
        }

    def capitalized(self, entry: Entry) -> Decimal:
        if entry.kind not in {"BUY", "SELL", "SHORT", "COVER"}:
            return ZERO
        return (entry.commission if self.capitalize_commissions else ZERO) + (
            entry.fee if self.capitalize_fees else ZERO
        )


@dataclass(frozen=True)
class Entry:
    id: str
    day: date
    kind: str
    currency: str
    quantity: Decimal = ZERO
    price: Decimal = ZERO
    fx: Decimal = ONE
    amount: Decimal = ZERO
    fee: Decimal = ZERO
    commission: Decimal = ZERO
    tax: Decimal = ZERO
    instrument_id: str | None = None
    multiplier: Decimal = ONE
    metadata: dict[str, Any] = field(default_factory=dict)
    settle_date: date | None = None
    account_id: str | None = None

    @property
    def charges(self) -> Decimal:
        return self.fee + self.commission + self.tax

    @property
    def gross(self) -> Decimal:
        return self.amount if self.amount else self.quantity * self.price * self.multiplier

    @property
    def settlement(self) -> date:
        return self.settle_date or self.day

    def validate(self) -> None:
        if not self.id or self.kind not in TRANSACTION_TYPES:
            raise ValueError("Entry requires an ID and supported transaction type")
        if (
            len(self.currency) != 3
            or not self.currency.isascii()
            or not self.currency.isalpha()
            or not self.currency.isupper()
        ):
            raise ValueError("Currency must be an uppercase three-letter code")
        for name in ("quantity", "price", "amount", "fee", "commission", "tax"):
            decimal(getattr(self, name), name, nonnegative=True)
        decimal(self.fx, "FX", positive=True)
        decimal(self.multiplier, "contract multiplier", positive=True)
        if self.settlement < self.day:
            raise ValueError("Settlement date cannot precede trade date")
        if self.kind in {"BUY", "SELL", "SHORT", "COVER"}:
            if not self.instrument_id or self.quantity <= ZERO or self.price <= ZERO:
                raise ValueError(
                    "A trade requires a known instrument and positive quantity and price"
                )
            if self.amount and self.amount != self.quantity * self.price * self.multiplier:
                raise ValueError("Gross amount must equal quantity times price times multiplier")


@dataclass
class OpenLot:
    id: str
    instrument_id: str
    entry_id: str
    opened: date
    direction: Direction
    quantity: Decimal
    native_basis: Decimal
    base_basis: Decimal
    multiplier: Decimal = ONE


@dataclass(frozen=True)
class LotMatch:
    lot_id: str
    opening_entry_id: str
    closing_entry_id: str
    instrument_id: str
    direction: Direction
    quantity: Decimal
    native_basis: Decimal
    base_basis: Decimal
    native_proceeds: Decimal
    base_proceeds: Decimal
    realised_native: Decimal
    realised_base: Decimal
    closed: date


@dataclass
class Lot:
    """Position rollup compatible with the persisted portfolio valuation contract."""

    quantity: Decimal = ZERO
    cost_native: Decimal = ZERO
    cost_base: Decimal = ZERO
    realised: Decimal = ZERO
    income: Decimal = ZERO
    charges: Decimal = ZERO
    multiplier: Decimal = ONE
    capitalized_charges: Decimal = ZERO

    @property
    def expensed_charges(self) -> Decimal:
        return self.charges - self.capitalized_charges
