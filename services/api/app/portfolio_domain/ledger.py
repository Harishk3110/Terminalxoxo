"""Deterministic transaction replay over cost-basis and settlement services."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from .cash import CashMovement, PortfolioCashService
from .cost_basis import CostBasisService
from .money import ONE, ZERO, decimal
from .types import SECURITY_MOVEMENTS, AccountingPolicy, Direction, Entry, Lot


@dataclass
class LedgerState:
    policy: AccountingPolicy = field(default_factory=AccountingPolicy)
    cash: dict[str, Decimal] = field(default_factory=dict)
    cash_book_base: Decimal = ZERO
    lots: dict[str, Lot] = field(default_factory=dict)
    external_flows: Decimal = ZERO
    income: Decimal = ZERO
    fees: Decimal = ZERO
    taxes: Decimal = ZERO
    adjustments: Decimal = ZERO
    capitalized_charges: Decimal = ZERO
    flow_events: list[tuple[date, Decimal]] = field(default_factory=list)
    cash_service: PortfolioCashService = field(default_factory=PortfolioCashService)
    cost_basis: CostBasisService = field(init=False)
    last_date: date | None = None

    def __post_init__(self) -> None:
        self.cost_basis = CostBasisService(self.policy)

    @property
    def expensed_fees(self) -> Decimal:
        return self.fees - self.capitalized_charges

    def move_cash(
        self, currency: str, amount: Decimal, fx: Decimal, *, entry: Entry, description: str
    ) -> None:
        if amount == ZERO:
            return
        self.cash_service.record(
            CashMovement(
                entry.id,
                currency,
                amount,
                fx,
                entry.day,
                entry.settlement,
                entry.account_id,
                description,
            )
        )
        self.cash[currency] = self.cash.get(currency, ZERO) + amount
        self.cash_book_base += amount * fx

    def external(self, entry: Entry, amount: Decimal) -> None:
        self.external_flows += amount
        self.flow_events.append((entry.day, amount))

    def _validate(self, entry: Entry) -> None:
        entry.validate()
        if self.last_date is not None and entry.day < self.last_date:
            raise ValueError("Ledger entries must be replayed in chronological order")
        cash_flow = entry.kind in {"DEPOSIT", "WITHDRAWAL", "DIVIDEND", "INTEREST"}
        cash_transfer = entry.kind in {"TRANSFER_IN", "TRANSFER_OUT"} and not entry.instrument_id
        if (cash_flow or cash_transfer) and entry.gross <= ZERO:
            raise ValueError("Cash flow must have an explicit positive amount")
        if entry.kind in {"COMMISSION", "FEE", "TAX"}:
            if entry.gross <= ZERO and entry.charges <= ZERO:
                raise ValueError("Expense amount must be positive")
            if entry.gross and entry.charges:
                raise ValueError("Expense must use either amount or charge fields, not both")
        if entry.kind == "OTHER_ADJUSTMENT":
            reason = entry.metadata.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                raise ValueError("A correcting adjustment requires a reason")
            if entry.metadata.get("direction") not in {"CREDIT", "DEBIT"} or entry.gross <= ZERO:
                raise ValueError("Adjustment requires CREDIT/DEBIT direction and positive amount")
        if entry.kind == "FX_CONVERSION":
            other = str(entry.metadata.get("to_currency", "")).upper()
            decimal(entry.metadata.get("to_amount", 0), "received amount", positive=True)
            if (
                len(other) != 3
                or not other.isascii()
                or not other.isalpha()
                or other == entry.currency
                or entry.gross <= ZERO
            ):
                raise ValueError("FX conversion requires two currencies and positive amounts")

    def apply(self, entry: Entry) -> None:
        self._validate(entry)
        gross, base = entry.gross, entry.gross * entry.fx
        if entry.kind in SECURITY_MOVEMENTS and entry.instrument_id:
            self._security_movement(entry)
        elif entry.kind in {"DEPOSIT", "WITHDRAWAL", "TRANSFER_IN", "TRANSFER_OUT"}:
            sign = ONE if entry.kind in {"DEPOSIT", "TRANSFER_IN"} else -ONE
            self.move_cash(
                entry.currency, sign * gross, entry.fx, entry=entry, description="CAPITAL"
            )
            self.external(entry, sign * base)
        elif entry.kind in {"DIVIDEND", "INTEREST"}:
            self.move_cash(entry.currency, gross, entry.fx, entry=entry, description="INCOME")
            self.income += base
            if entry.instrument_id:
                self.lots.setdefault(entry.instrument_id, Lot()).income += base
        elif entry.kind in {"COMMISSION", "FEE", "TAX"}:
            self._expense(entry)
            self.last_date = entry.day
            return
        elif entry.kind == "FX_CONVERSION":
            received = decimal(entry.metadata["to_amount"], "received amount", positive=True)
            other = str(entry.metadata["to_currency"]).upper()
            self.move_cash(entry.currency, -gross, entry.fx, entry=entry, description="FX_SOLD")
            self.move_cash(other, received, base / received, entry=entry, description="FX_BOUGHT")
        elif entry.kind in {"SPLIT", "REVERSE_SPLIT", "SPINOFF", "MERGER"}:
            self._corporate_action(entry)
        elif entry.kind == "OTHER_ADJUSTMENT":
            sign = ONE if entry.metadata["direction"] == "CREDIT" else -ONE
            self.move_cash(
                entry.currency, sign * gross, entry.fx, entry=entry, description="ADJUSTMENT"
            )
            self.adjustments += sign * base
        self._charges(entry)
        self.last_date = entry.day

    def _security_movement(self, entry: Entry) -> None:
        assert entry.instrument_id is not None
        if entry.kind in {"BUY", "TRANSFER_IN", "SHORT"}:
            direction = Direction.SHORT if entry.kind == "SHORT" else Direction.LONG
            self.cost_basis.open_position(entry, direction)
            realised = ZERO
        else:
            direction = Direction.SHORT if entry.kind == "COVER" else Direction.LONG
            matches = self.cost_basis.close_position(entry, direction)
            realised = sum((match.realised_base for match in matches), ZERO)
        lot = self.lots.setdefault(entry.instrument_id, Lot())
        self.cost_basis.rollup(entry.instrument_id, lot)
        lot.realised += realised
        if entry.kind in {"TRANSFER_IN", "TRANSFER_OUT"}:
            sign = ONE if entry.kind == "TRANSFER_IN" else -ONE
            self.external(entry, sign * entry.gross * entry.fx)
        else:
            sign = ONE if entry.kind in {"SELL", "SHORT"} else -ONE
            self.move_cash(
                entry.currency, sign * entry.gross, entry.fx, entry=entry, description="TRADE"
            )

    def _expense(self, entry: Entry) -> None:
        charge = entry.gross or entry.charges
        self.move_cash(entry.currency, -charge, entry.fx, entry=entry, description=entry.kind)
        if entry.kind == "TAX":
            self.taxes += charge * entry.fx
        else:
            self.fees += charge * entry.fx
        if entry.instrument_id:
            self.lots.setdefault(entry.instrument_id, Lot()).charges += charge * entry.fx

    def _charges(self, entry: Entry) -> None:
        self.move_cash(entry.currency, -entry.charges, entry.fx, entry=entry, description="CHARGES")
        self.fees += (entry.fee + entry.commission) * entry.fx
        self.taxes += entry.tax * entry.fx
        capitalized = self.policy.capitalized(entry) * entry.fx
        self.capitalized_charges += capitalized
        if entry.instrument_id:
            lot = self.lots.setdefault(entry.instrument_id, Lot())
            lot.charges += entry.charges * entry.fx
            lot.capitalized_charges += capitalized

    def _corporate_action(self, entry: Entry) -> None:
        instrument_id = entry.instrument_id or ""
        if entry.kind in {"SPLIT", "REVERSE_SPLIT"}:
            ratio = decimal(
                entry.metadata.get("ratio", entry.quantity), "split ratio", positive=True
            )
            if entry.kind == "REVERSE_SPLIT" and ratio >= ONE:
                raise ValueError("Reverse split ratio must be below one")
            self.cost_basis.split(instrument_id, ratio)
        else:
            child_id = entry.metadata.get("child_instrument_id")
            if not isinstance(child_id, str) or not child_id:
                raise ValueError("Corporate action requires a child instrument")
            if entry.kind == "SPINOFF":
                allocation = decimal(
                    entry.metadata.get("cost_allocation", 0), "cost allocation", nonnegative=True
                )
                self.cost_basis.spinoff(entry, child_id, allocation)
            else:
                ratio = decimal(
                    entry.metadata.get("exchange_ratio", 0), "exchange ratio", positive=True
                )
                cash = decimal(
                    entry.metadata.get("cash_per_share", 0), "cash per share", nonnegative=True
                )
                allocation = decimal(
                    entry.metadata.get("cash_cost_allocation", 0),
                    "cash cost allocation",
                    nonnegative=True,
                )
                received, realised = self.cost_basis.merger(
                    entry, child_id, ratio, cash, allocation
                )
                self.move_cash(
                    entry.currency, received, entry.fx, entry=entry, description="MERGER_CASH"
                )
                self.lots.setdefault(instrument_id, Lot()).realised += realised
            self.cost_basis.rollup(child_id, self.lots.setdefault(child_id, Lot()))
        self.cost_basis.rollup(instrument_id, self.lots.setdefault(instrument_id, Lot()))

    def advance(self, day: date) -> None:
        if self.last_date is not None and day < self.last_date:
            raise ValueError("Ledger valuation date cannot move backwards")
        self.last_date = day
