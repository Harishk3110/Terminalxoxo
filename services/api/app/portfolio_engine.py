"""Pure, Decimal-based portfolio accounting; no database or HTTP dependencies."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN
from typing import Any

ZERO = Decimal("0")
ONE = Decimal("1")
TRANSACTION_TYPES = {
    "DEPOSIT", "WITHDRAWAL", "BUY", "SELL", "SHORT", "COVER", "DIVIDEND",
    "INTEREST", "COMMISSION", "FEE", "TAX", "FX_CONVERSION", "SPLIT",
    "SPINOFF", "TRANSFER_IN", "TRANSFER_OUT", "OTHER_ADJUSTMENT",
}
ASSET_BUCKETS = {"accrued_income", "receivables"}
LIABILITY_BUCKETS = {"payables", "accrued_fees", "other_liabilities"}


def decimal(value: Any, name="amount", *, positive=False, nonnegative=False) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc
    if not result.is_finite() or abs(result) > Decimal("1e16"):
        raise ValueError(f"{name} must be finite and within accounting bounds")
    if positive and result <= 0 or nonnegative and result < 0:
        raise ValueError(f"{name} must be {'positive' if positive else 'non-negative'}")
    return result


def money(value: Decimal) -> Decimal:
    rounded = value.quantize(Decimal(".01"), rounding=ROUND_HALF_EVEN)
    return abs(rounded) if rounded == 0 else rounded


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
    metadata: dict = field(default_factory=dict)

    @property
    def charges(self):
        return self.fee + self.commission + self.tax

    @property
    def gross(self):
        return self.amount if self.amount else self.quantity * self.price * self.multiplier


@dataclass
class Lot:
    quantity: Decimal = ZERO
    cost_native: Decimal = ZERO
    cost_base: Decimal = ZERO
    realised: Decimal = ZERO
    income: Decimal = ZERO
    charges: Decimal = ZERO
    multiplier: Decimal = ONE


@dataclass
class LedgerState:
    cash: dict[str, Decimal] = field(default_factory=dict)
    cash_book_base: Decimal = ZERO
    lots: dict[str, Lot] = field(default_factory=dict)
    external_flows: Decimal = ZERO
    income: Decimal = ZERO
    fees: Decimal = ZERO
    taxes: Decimal = ZERO
    adjustments: Decimal = ZERO
    flow_events: list[tuple[date, Decimal]] = field(default_factory=list)

    def move_cash(self, currency: str, amount: Decimal, fx: Decimal = ONE):
        self.cash[currency] = self.cash.get(currency, ZERO) + amount
        self.cash_book_base += amount * fx

    def external(self, entry: Entry, amount: Decimal):
        self.external_flows += amount
        self.flow_events.append((entry.day, amount))

    def apply(self, entry: Entry):
        if entry.kind not in TRANSACTION_TYPES:
            raise ValueError("Unsupported transaction type")
        for name in ("quantity", "price", "amount", "fee", "commission", "tax"):
            decimal(getattr(entry, name), name, nonnegative=True)
        decimal(entry.fx, "FX", positive=True)
        decimal(entry.multiplier, "contract multiplier", positive=True)
        gross, base = entry.gross, entry.gross * entry.fx
        lot = self.lots.setdefault(entry.instrument_id, Lot()) if entry.instrument_id else None
        if lot and lot.quantity and lot.multiplier != entry.multiplier:
            raise ValueError("Contract multiplier cannot change without an explicit adjustment")
        if lot:
            lot.multiplier = entry.multiplier

        if entry.kind in {"BUY", "SELL", "SHORT", "COVER", "TRANSFER_IN", "TRANSFER_OUT"} and lot:
            if entry.quantity <= 0 or entry.price <= 0:
                raise ValueError("Security movements require positive quantity and price")
            q = entry.quantity
            if entry.kind in {"BUY", "TRANSFER_IN"}:
                if lot.quantity < 0:
                    raise ValueError("Use COVER to close a short position")
                lot.quantity += q
                lot.cost_native += gross
                lot.cost_base += base
                if entry.kind == "BUY":
                    self.move_cash(entry.currency, -gross, entry.fx)
                else:
                    self.external(entry, base)
            elif entry.kind in {"SELL", "TRANSFER_OUT"}:
                if q > lot.quantity:
                    raise ValueError("Sale or transfer exceeds holdings on the trade date")
                native_cost = lot.cost_native * q / lot.quantity
                base_cost = lot.cost_base * q / lot.quantity
                lot.quantity -= q
                lot.cost_native -= native_cost
                lot.cost_base -= base_cost
                lot.realised += base - base_cost
                if entry.kind == "SELL":
                    self.move_cash(entry.currency, gross, entry.fx)
                else:
                    self.external(entry, -base)
            elif entry.kind == "SHORT":
                if lot.quantity > 0:
                    raise ValueError("Close the long position before opening a short")
                lot.quantity -= q
                lot.cost_native -= gross
                lot.cost_base -= base
                self.move_cash(entry.currency, gross, entry.fx)
            else:
                if q > -lot.quantity:
                    raise ValueError("Cover exceeds the recorded short position")
                native_cost = -lot.cost_native * q / -lot.quantity
                base_cost = -lot.cost_base * q / -lot.quantity
                lot.quantity += q
                lot.cost_native += native_cost
                lot.cost_base += base_cost
                lot.realised += base_cost - base
                self.move_cash(entry.currency, -gross, entry.fx)
        elif entry.kind in {"BUY", "SELL", "SHORT", "COVER"}:
            raise ValueError("A trade requires a known instrument")
        elif entry.kind in {"DEPOSIT", "WITHDRAWAL", "TRANSFER_IN", "TRANSFER_OUT"}:
            if gross <= 0:
                raise ValueError("External cash flow must have an explicit positive amount")
            sign = ONE if entry.kind in {"DEPOSIT", "TRANSFER_IN"} else -ONE
            self.move_cash(entry.currency, sign * gross, entry.fx)
            self.external(entry, sign * base)
        elif entry.kind in {"DIVIDEND", "INTEREST"}:
            if gross <= 0:
                raise ValueError("Income must have an explicit positive amount")
            self.move_cash(entry.currency, gross, entry.fx)
            self.income += base
            if lot:
                lot.income += base
        elif entry.kind in {"COMMISSION", "FEE", "TAX"}:
            charge = gross if gross else entry.charges
            if charge <= 0:
                raise ValueError("Expense amount must be positive")
            self.move_cash(entry.currency, -charge, entry.fx)
            if entry.kind == "TAX":
                self.taxes += charge * entry.fx
            else:
                self.fees += charge * entry.fx
            if lot:
                lot.charges += charge * entry.fx
            return
        elif entry.kind == "FX_CONVERSION":
            other = str(entry.metadata.get("to_currency", "")).upper()
            received = decimal(entry.metadata.get("to_amount", 0), "received amount", positive=True)
            if not other or other == entry.currency or gross <= 0:
                raise ValueError("FX conversion requires two currencies and positive amounts")
            self.move_cash(entry.currency, -gross, entry.fx)
            self.move_cash(other, received, base / received)
        elif entry.kind == "SPLIT":
            if not lot or lot.quantity == 0:
                raise ValueError("A split requires an existing position")
            ratio = decimal(entry.metadata.get("ratio", entry.quantity), "split ratio", positive=True)
            lot.quantity *= ratio
        elif entry.kind == "SPINOFF":
            if not lot or lot.quantity <= 0:
                raise ValueError("A spinoff requires a long parent position")
            child_id = entry.metadata.get("child_instrument_id")
            allocation = decimal(entry.metadata.get("cost_allocation", 0), "cost allocation", nonnegative=True)
            if not child_id or child_id == entry.instrument_id or allocation >= 1 or entry.quantity <= 0:
                raise ValueError("Spinoff requires child, quantity and a cost allocation below one")
            child = self.lots.setdefault(child_id, Lot())
            child.quantity += entry.quantity
            child.cost_native += lot.cost_native * allocation
            child.cost_base += lot.cost_base * allocation
            lot.cost_native *= ONE - allocation
            lot.cost_base *= ONE - allocation
        elif entry.kind == "OTHER_ADJUSTMENT":
            if not entry.metadata.get("reason") or entry.metadata.get("direction") not in {"CREDIT", "DEBIT"}:
                raise ValueError("A correcting adjustment requires a reason and CREDIT/DEBIT direction")
            sign = ONE if entry.metadata["direction"] == "CREDIT" else -ONE
            self.move_cash(entry.currency, sign * gross, entry.fx)
            self.adjustments += sign * base
        self.move_cash(entry.currency, -entry.charges, entry.fx)
        self.fees += (entry.fee + entry.commission) * entry.fx
        self.taxes += entry.tax * entry.fx
        if lot:
            lot.charges += entry.charges * entry.fx


def nav_total(cash: Decimal, positions: list[Decimal], balances: dict[str, Decimal]):
    unknown = set(balances) - ASSET_BUCKETS - LIABILITY_BUCKETS
    if unknown:
        raise ValueError(f"Unknown NAV balance bucket: {sorted(unknown)}")
    assets = sum((balances.get(k, ZERO) for k in ASSET_BUCKETS), ZERO)
    liabilities = sum((balances.get(k, ZERO) for k in LIABILITY_BUCKETS), ZERO)
    invested = sum(positions, ZERO)
    gross_assets = max(cash, ZERO) + sum((max(v, ZERO) for v in positions), ZERO) + assets
    return {
        "nav": cash + invested + assets - liabilities,
        "cash": cash, "market_value": invested, "gross_asset_value": gross_assets,
        "accrued_income": balances.get("accrued_income", ZERO),
        "receivables": balances.get("receivables", ZERO),
        "liabilities": liabilities, **balances,
    }


def daily_performance(opening: Decimal, closing: Decimal, flows: Decimal):
    pnl = closing - opening - flows
    denominator = opening + flows
    return pnl, (pnl / denominator if denominator > 0 else None)
