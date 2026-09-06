"""Position-period P&L from observed marks, recorded cash and explicit capital transfers."""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from .cash import CashMovement
from .money import ONE, ZERO, decimal
from .types import Entry

METHOD = (
    "Closing marked value minus opening marked value plus recorded economic cash "
    "minus external security flows minus internal corporate-action transfers. "
    "Corporate-action reference value follows the recorded cost-allocation fraction; "
    "same-day purchases enter at recorded gross consideration. No missing mark is zero-filled."
)


@dataclass(frozen=True)
class PositionPeriodPnl:
    instrument_id: str
    opening_value: Decimal | None
    closing_value: Decimal | None
    economic_cash: Decimal
    external_security_flow: Decimal
    internal_transfer: Decimal | None
    pnl: Decimal | None
    warnings: tuple[str, ...]

    def payload(self) -> dict[str, str | list[str] | None]:
        return {
            "instrument_id": self.instrument_id,
            "opening_value": str(self.opening_value) if self.opening_value is not None else None,
            "closing_value": str(self.closing_value) if self.closing_value is not None else None,
            "economic_cash": str(self.economic_cash),
            "external_security_flow": str(self.external_security_flow),
            "internal_transfer": str(self.internal_transfer)
            if self.internal_transfer is not None
            else None,
            "pnl": str(self.pnl) if self.pnl is not None else None,
            "state": "AVAILABLE" if self.pnl is not None else "UNAVAILABLE",
            "methodology": METHOD,
            "warnings": list(self.warnings),
        }


class PositionPnlSession:
    """One valuation interval; feed only entries successfully applied by the ledger."""

    def __init__(
        self,
        opening_quantities: Mapping[str, Decimal],
        opening_values: Mapping[str, Decimal | None],
    ):
        self.quantities = dict(opening_quantities)
        self.opening: dict[str, Decimal | None] = {
            key: opening_values.get(key) for key, quantity in opening_quantities.items() if quantity
        }
        self.reference = dict(self.opening)
        self.transfers: dict[str, Decimal | None] = {}
        self.external: dict[str, Decimal] = defaultdict(Decimal)
        self.entries: dict[str, Entry] = {}
        self.warnings: dict[str, list[str]] = defaultdict(list)

    def _add_reference(self, key: str, amount: Decimal | None) -> None:
        old = self.reference.get(key, ZERO)
        self.reference[key] = old + amount if old is not None and amount is not None else None

    def _transfer(self, parent: str, child: str, fraction: Decimal) -> None:
        decimal(fraction, "reference allocation", nonnegative=True)
        if fraction > ONE or parent == child:
            raise ValueError(
                "Corporate allocation requires distinct instruments and a fraction at most one"
            )
        value = self.reference.get(parent, ZERO)
        transferred = value * fraction if value is not None else None
        for key, sign in ((parent, -ONE), (child, ONE)):
            old = self.transfers.get(key, ZERO)
            delta = transferred * sign if transferred is not None else None
            self.transfers[key] = old + delta if old is not None and delta is not None else None
            self._add_reference(key, delta)
            if transferred is None:
                self.warnings[key].append("Corporate transfer reference value is unavailable")

    def _remove_units(self, key: str, amount: Decimal) -> None:
        old = self.quantities.get(key, ZERO)
        if old == ZERO or amount > abs(old):
            raise ValueError("Attribution closing units exceed the recorded position")
        remaining = abs(old) - amount
        value = self.reference.get(key, ZERO)
        self.reference[key] = value * remaining / abs(old) if value is not None else None
        self.quantities[key] = remaining if old > ZERO else -remaining
        if remaining == ZERO:
            self.reference[key] = ZERO

    def record(self, entry: Entry) -> None:
        entry.validate()
        if entry.id in self.entries:
            raise ValueError("Attribution interval contains a duplicate transaction")
        self.entries[entry.id] = entry
        key = entry.instrument_id
        if key is None:
            return
        quantity = self.quantities.get(key, ZERO)
        if entry.kind in {"BUY", "SHORT", "TRANSFER_IN"}:
            sign = -ONE if entry.kind == "SHORT" else ONE
            self.quantities[key] = quantity + sign * entry.quantity
            self._add_reference(key, sign * entry.gross * entry.fx)
        elif entry.kind in {"SELL", "COVER", "TRANSFER_OUT"}:
            self._remove_units(key, entry.quantity)
        elif entry.kind in {"SPLIT", "REVERSE_SPLIT"}:
            ratio = decimal(
                entry.metadata.get("ratio", entry.quantity), "split ratio", positive=True
            )
            self.quantities[key] = quantity * ratio
        elif entry.kind in {"SPINOFF", "MERGER"}:
            child = entry.metadata.get("child_instrument_id")
            if not isinstance(child, str) or not child:
                raise ValueError("Corporate attribution requires a successor instrument")
            if entry.kind == "SPINOFF":
                fraction = decimal(
                    entry.metadata.get("cost_allocation", 0), "cost allocation", nonnegative=True
                )
                self._transfer(key, child, fraction)
                self.quantities[child] = self.quantities.get(child, ZERO) + entry.quantity
            else:
                cash_fraction = decimal(
                    entry.metadata.get("cash_cost_allocation", 0),
                    "cash cost allocation",
                    nonnegative=True,
                )
                self._transfer(key, child, ONE - cash_fraction)
                ratio = decimal(
                    entry.metadata.get("exchange_ratio", 0), "exchange ratio", positive=True
                )
                self.quantities[child] = self.quantities.get(child, ZERO) + quantity * ratio
                self.quantities[key] = ZERO
                self.reference[key] = ZERO
        if entry.kind in {"TRANSFER_IN", "TRANSFER_OUT"}:
            sign = ONE if entry.kind == "TRANSFER_IN" else -ONE
            self.external[key] += sign * entry.gross * entry.fx

    def finish(
        self,
        closing_values: Mapping[str, Decimal | None],
        movements: Iterable[CashMovement],
    ) -> dict[str, PositionPeriodPnl]:
        cash: dict[str, Decimal] = defaultdict(Decimal)
        cash_kinds = {
            "BUY",
            "SELL",
            "SHORT",
            "COVER",
            "DIVIDEND",
            "INTEREST",
            "COMMISSION",
            "FEE",
            "TAX",
            "TRANSFER_IN",
            "TRANSFER_OUT",
            "SPLIT",
            "REVERSE_SPLIT",
            "SPINOFF",
            "MERGER",
        }
        for movement in movements:
            entry = self.entries.get(movement.transaction_id)
            if entry and entry.instrument_id and entry.kind in cash_kinds:
                cash[entry.instrument_id] += movement.amount * movement.fx
        keys = (
            set(self.opening)
            | set(closing_values)
            | set(cash)
            | set(self.external)
            | set(self.transfers)
        )
        keys.update(entry.instrument_id for entry in self.entries.values() if entry.instrument_id)
        result = {}
        for key in sorted(keys):
            opening = self.opening.get(key, ZERO)
            closing = closing_values.get(key) if self.quantities.get(key, ZERO) else ZERO
            transferred = self.transfers.get(key, ZERO)
            warnings = list(self.warnings.get(key, []))
            if opening is None:
                warnings.append("Opening position mark is unavailable")
            if closing is None:
                warnings.append("Closing position mark is unavailable")
            pnl = None
            if opening is not None and closing is not None and transferred is not None:
                pnl = closing - opening + cash[key] - self.external[key] - transferred
            result[key] = PositionPeriodPnl(
                key,
                opening,
                closing,
                cash[key],
                self.external[key],
                transferred,
                pnl,
                tuple(dict.fromkeys(warnings)),
            )
        return result
