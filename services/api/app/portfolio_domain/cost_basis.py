"""Weighted-average and FIFO lot matching with explicit cost treatment."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from .money import ONE, ZERO, allocate, decimal
from .types import AccountingPolicy, CostMethod, Direction, Entry, Lot, LotMatch, OpenLot


@dataclass
class CostBasisService:
    policy: AccountingPolicy = field(default_factory=AccountingPolicy)
    open_lots: dict[str, list[OpenLot]] = field(default_factory=dict)
    matches: list[LotMatch] = field(default_factory=list)

    def lots_for(self, instrument_id: str) -> list[OpenLot]:
        return sorted(
            (lot for lot in self.open_lots.get(instrument_id, []) if lot.quantity > ZERO),
            key=lambda lot: lot.opened,
        )

    def rollup(self, instrument_id: str, position: Lot) -> None:
        lots = self.lots_for(instrument_id)
        position.quantity = sum(
            (lot.quantity if lot.direction == Direction.LONG else -lot.quantity for lot in lots),
            ZERO,
        )
        position.cost_native = sum(
            (
                lot.native_basis if lot.direction == Direction.LONG else -lot.native_basis
                for lot in lots
            ),
            ZERO,
        )
        position.cost_base = sum(
            (
                lot.base_basis if lot.direction == Direction.LONG else -lot.base_basis
                for lot in lots
            ),
            ZERO,
        )
        if lots:
            position.multiplier = lots[0].multiplier

    def open_position(self, entry: Entry, direction: Direction) -> OpenLot:
        entry.validate()
        if not entry.instrument_id or entry.quantity <= ZERO or entry.price <= ZERO:
            raise ValueError("Security movements require positive quantity and price")
        lots = self.lots_for(entry.instrument_id)
        if any(lot.direction != direction for lot in lots):
            command = "COVER" if direction == Direction.LONG else "SELL"
            raise ValueError(f"Use {command} to close the existing opposite position")
        if any(lot.multiplier != entry.multiplier for lot in lots):
            raise ValueError("Contract multiplier cannot change without an explicit adjustment")
        cost = self.policy.capitalized(entry)
        basis = entry.gross + cost if direction == Direction.LONG else entry.gross - cost
        sequence = len(self.open_lots.get(entry.instrument_id, []))
        identifier = str(
            uuid5(NAMESPACE_URL, f"knk-lot:{entry.id}:{entry.instrument_id}:{sequence}")
        )
        lot = OpenLot(
            identifier,
            entry.instrument_id,
            entry.id,
            entry.day,
            direction,
            entry.quantity,
            basis,
            basis * entry.fx,
            entry.multiplier,
        )
        self.open_lots.setdefault(entry.instrument_id, []).append(lot)
        return lot

    def close_position(self, entry: Entry, direction: Direction) -> list[LotMatch]:
        entry.validate()
        if not entry.instrument_id or entry.quantity <= ZERO or entry.price <= ZERO:
            raise ValueError("Security movements require positive quantity and price")
        lots = self.lots_for(entry.instrument_id)
        if any(lot.direction != direction for lot in lots):
            raise ValueError("Closing side does not match the recorded position")
        available = sum((lot.quantity for lot in lots), ZERO)
        if entry.quantity > available:
            label = "Cover" if direction == Direction.SHORT else "Sale or transfer"
            raise ValueError(f"{label} exceeds holdings on the trade date")
        if any(lot.multiplier != entry.multiplier for lot in lots):
            raise ValueError("Contract multiplier does not match the open position")
        amounts = self._matched_quantities(lots, entry.quantity)
        cost = self.policy.capitalized(entry)
        proceeds = entry.gross - cost if direction == Direction.LONG else entry.gross + cost
        allocated_proceeds = allocate(proceeds, amounts)
        base_proceeds = allocate(proceeds * entry.fx, amounts)
        matches: list[LotMatch] = []
        for lot, quantity, native_value, base_value in zip(
            lots, amounts, allocated_proceeds, base_proceeds, strict=True
        ):
            if quantity == ZERO:
                continue
            native_basis = (
                lot.native_basis
                if quantity == lot.quantity
                else lot.native_basis * quantity / lot.quantity
            )
            base_basis = (
                lot.base_basis
                if quantity == lot.quantity
                else lot.base_basis * quantity / lot.quantity
            )
            sign = ONE if direction == Direction.LONG else -ONE
            match = LotMatch(
                lot.id,
                lot.entry_id,
                entry.id,
                entry.instrument_id,
                direction,
                quantity,
                native_basis,
                base_basis,
                native_value,
                base_value,
                sign * (native_value - native_basis),
                sign * (base_value - base_basis),
                entry.day,
            )
            lot.quantity -= quantity
            lot.native_basis -= native_basis
            lot.base_basis -= base_basis
            matches.append(match)
        self.matches.extend(matches)
        return matches

    def _matched_quantities(self, lots: list[OpenLot], quantity: Decimal) -> list[Decimal]:
        if quantity == sum((lot.quantity for lot in lots), ZERO):
            return [lot.quantity for lot in lots]
        if self.policy.method == CostMethod.AVERAGE:
            return allocate(quantity, [lot.quantity for lot in lots])
        remaining = quantity
        result = []
        for lot in lots:
            matched = min(remaining, lot.quantity)
            result.append(matched)
            remaining -= matched
        return result

    def split(self, instrument_id: str, ratio: Decimal) -> None:
        decimal(ratio, "split ratio", positive=True)
        lots = self.lots_for(instrument_id)
        if not lots:
            raise ValueError("A split requires an existing position and positive ratio")
        for lot in lots:
            lot.quantity *= ratio

    def spinoff(self, entry: Entry, child_id: str, allocation: Decimal) -> None:
        entry.validate()
        decimal(allocation, "cost allocation", nonnegative=True)
        parent = self.lots_for(entry.instrument_id or "")
        child = self.lots_for(child_id)
        if not parent or any(lot.direction != Direction.LONG for lot in parent):
            raise ValueError("A spinoff requires a long parent position")
        if not child_id or child_id == entry.instrument_id or entry.quantity <= ZERO:
            raise ValueError("Spinoff requires a distinct child and positive quantity")
        if not ZERO <= allocation < ONE or any(lot.direction != Direction.LONG for lot in child):
            raise ValueError(
                "Spinoff requires a cost allocation below one and no short child position"
            )
        if any(lot.multiplier != ONE for lot in parent + child):
            raise ValueError("Spinoff securities must use unit multipliers")
        quantities = allocate(entry.quantity, [lot.quantity for lot in parent])
        created = []
        for lot, quantity in zip(parent, quantities, strict=True):
            native, base = lot.native_basis * allocation, lot.base_basis * allocation
            child_lot = OpenLot(
                str(uuid5(NAMESPACE_URL, f"knk-spinoff:{entry.id}:{lot.id}")),
                child_id,
                entry.id,
                lot.opened,
                Direction.LONG,
                quantity,
                native,
                base,
            )
            lot.native_basis -= native
            lot.base_basis -= base
            created.append(child_lot)
        self.open_lots.setdefault(child_id, []).extend(created)

    def merger(
        self,
        entry: Entry,
        child_id: str,
        ratio: Decimal,
        cash_per_share: Decimal,
        cash_cost_allocation: Decimal,
    ) -> tuple[Decimal, Decimal]:
        entry.validate()
        decimal(ratio, "exchange ratio", positive=True)
        decimal(cash_per_share, "cash per share", nonnegative=True)
        decimal(cash_cost_allocation, "cash cost allocation", nonnegative=True)
        parent = self.lots_for(entry.instrument_id or "")
        if not parent or any(lot.direction != Direction.LONG for lot in parent):
            raise ValueError("A merger requires an existing long parent position")
        if not child_id or child_id == entry.instrument_id or ratio <= ZERO:
            raise ValueError("Merger requires a distinct successor and positive exchange ratio")
        if cash_per_share < ZERO or not ZERO <= cash_cost_allocation <= ONE:
            raise ValueError("Invalid merger cash or cash cost allocation")
        if cash_per_share == ZERO and cash_cost_allocation != ZERO:
            raise ValueError("A stock-only merger cannot allocate basis to cash")
        if any(lot.multiplier != ONE for lot in parent):
            raise ValueError("Merger parent must use a unit multiplier")
        if any(
            lot.direction != Direction.LONG or lot.multiplier != ONE
            for lot in self.lots_for(child_id)
        ):
            raise ValueError("Successor must not be short or have a non-unit multiplier")
        cash = ZERO
        realised = ZERO
        successor_lots = []
        for lot in parent:
            native_cash = lot.quantity * cash_per_share
            basis_native = lot.native_basis * cash_cost_allocation
            basis_base = lot.base_basis * cash_cost_allocation
            cash += native_cash
            realised += native_cash * entry.fx - basis_base
            successor_lots.append(
                OpenLot(
                    str(uuid5(NAMESPACE_URL, f"knk-merger:{entry.id}:{lot.id}")),
                    child_id,
                    entry.id,
                    lot.opened,
                    Direction.LONG,
                    lot.quantity * ratio,
                    lot.native_basis - basis_native,
                    lot.base_basis - basis_base,
                )
            )
            self.matches.append(
                LotMatch(
                    lot.id,
                    lot.entry_id,
                    entry.id,
                    lot.instrument_id,
                    Direction.LONG,
                    lot.quantity,
                    basis_native,
                    basis_base,
                    native_cash,
                    native_cash * entry.fx,
                    native_cash - basis_native,
                    native_cash * entry.fx - basis_base,
                    entry.day,
                )
            )
            lot.quantity = ZERO
            lot.native_basis = ZERO
            lot.base_basis = ZERO
        self.open_lots.setdefault(child_id, []).extend(successor_lots)
        return cash, realised
