"""Signed position valuation and transparent unrealised price/FX decomposition."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict

from .money import ZERO, money
from .types import Lot

PositionPayload = TypedDict(
    "PositionPayload",
    {
        "direction": str,
        "quantity": Decimal,
        "contract_multiplier": Decimal,
        "average_cost": Decimal | None,
        "cost_basis_native": Decimal,
        "cost_basis_base": Decimal,
        "market_price": Decimal | None,
        "market_value_native": Decimal | None,
        "market_value_base_exact": Decimal | None,
        "market_value": Decimal | None,
        "unrealised_pnl_native": Decimal | None,
        "unrealised_pnl": Decimal | None,
        "unrealised_price_pnl_base": Decimal | None,
        "unrealised_fx_pnl_base": Decimal | None,
        "realised_pnl": Decimal,
        "income": Decimal,
        "fees": Decimal,
        "capitalized_charges": Decimal,
        "expensed_charges": Decimal,
        "total_pnl": Decimal | None,
        # The valuation layer normalizes this ratio to float, not monetary fields.
        "return": Decimal | float | None,
        "valuation_state": str,
        "valuation_warnings": list[str],
        "unrealised_decomposition_method": str,
    },
)


class PositionExposure(TypedDict):
    nav_weight: Decimal | None
    sector_weight: Decimal | None
    beta_contribution: Decimal | None


@dataclass(frozen=True)
class PositionMeasurement:
    quantity: Decimal
    multiplier: Decimal
    price: Decimal | None
    fx: Decimal | None
    cost_native: Decimal
    cost_base: Decimal
    realised_base: Decimal
    income_base: Decimal
    charges_base: Decimal
    capitalized_base: Decimal
    native_value: Decimal | None
    base_value: Decimal | None
    unrealised_native: Decimal | None
    unrealised_base: Decimal | None
    price_pnl_base: Decimal | None
    fx_pnl_base: Decimal | None
    warnings: tuple[str, ...]

    @property
    def direction(self) -> str:
        return "LONG" if self.quantity > ZERO else "SHORT" if self.quantity < ZERO else "CLOSED"

    @property
    def expensed_charges(self) -> Decimal:
        return self.charges_base - self.capitalized_base

    @property
    def total_pnl(self) -> Decimal | None:
        if self.unrealised_base is None:
            return None
        return self.unrealised_base + self.realised_base + self.income_base - self.expensed_charges

    def payload(self) -> PositionPayload:
        return {
            "direction": self.direction,
            "quantity": self.quantity,
            "contract_multiplier": self.multiplier,
            "average_cost": self.cost_native / self.quantity / self.multiplier
            if self.quantity
            else None,
            "cost_basis_native": self.cost_native,
            "cost_basis_base": self.cost_base,
            "market_price": self.price,
            "market_value_native": self.native_value,
            "market_value_base_exact": self.base_value,
            "market_value": money(self.base_value) if self.base_value is not None else None,
            "unrealised_pnl_native": self.unrealised_native,
            "unrealised_pnl": money(self.unrealised_base)
            if self.unrealised_base is not None
            else None,
            "unrealised_price_pnl_base": self.price_pnl_base,
            "unrealised_fx_pnl_base": self.fx_pnl_base,
            "realised_pnl": money(self.realised_base),
            "income": money(self.income_base),
            "fees": money(self.charges_base),
            "capitalized_charges": money(self.capitalized_base),
            "expensed_charges": money(self.expensed_charges),
            "total_pnl": money(self.total_pnl) if self.total_pnl is not None else None,
            "return": self.unrealised_base / abs(self.cost_base)
            if self.unrealised_base is not None and self.cost_base
            else None,
            "valuation_state": "AVAILABLE" if self.base_value is not None else "UNAVAILABLE",
            "valuation_warnings": list(self.warnings),
            "unrealised_decomposition_method": "Price component = (native market value - native basis) x current FX; FX component = native basis x current FX - recorded base basis",
        }


class PortfolioPositionService:
    @staticmethod
    def measure(lot: Lot, price: Decimal | None, fx: Decimal | None) -> PositionMeasurement:
        inputs = (
            lot.quantity,
            lot.multiplier,
            lot.cost_native,
            lot.cost_base,
            lot.realised,
            lot.income,
            lot.charges,
            lot.capitalized_charges,
        )
        if any(not value.is_finite() for value in inputs):
            raise ValueError("Position balances must be finite")
        if lot.multiplier <= ZERO:
            raise ValueError("Position contract multiplier must be positive")
        if not lot.quantity and (lot.cost_native or lot.cost_base):
            raise ValueError("A closed position cannot retain an open cost basis")
        if price is not None and (not price.is_finite() or price < ZERO):
            raise ValueError("Marked price must be finite and non-negative")
        if fx is not None and (not fx.is_finite() or fx <= ZERO):
            raise ValueError("Marked FX must be finite and positive")
        warnings: list[str] = []
        if price is None and lot.quantity:
            warnings.append("Position price is unavailable")
        if fx is None and lot.quantity:
            warnings.append("Position FX is unavailable")
        native = lot.quantity * lot.multiplier * price if price is not None else None
        if not lot.quantity:
            native = ZERO
        base = native * fx if native is not None and fx is not None else None
        if not lot.quantity:
            base = ZERO
        unrealised_native = native - lot.cost_native if native is not None else None
        unrealised_base = base - lot.cost_base if base is not None else None
        price_pnl = (
            unrealised_native * fx if unrealised_native is not None and fx is not None else None
        )
        fx_pnl = lot.cost_native * fx - lot.cost_base if fx is not None else None
        if not lot.quantity and not lot.cost_native and not lot.cost_base:
            price_pnl = fx_pnl = ZERO
        return PositionMeasurement(
            lot.quantity,
            lot.multiplier,
            price,
            fx,
            lot.cost_native,
            lot.cost_base,
            lot.realised,
            lot.income,
            lot.charges,
            lot.capitalized_charges,
            native,
            base,
            unrealised_native,
            unrealised_base,
            price_pnl,
            fx_pnl,
            tuple(warnings),
        )


@dataclass(frozen=True)
class ExposurePosition:
    instrument_id: str
    sector: str
    base_value: Decimal | None
    beta: Decimal | None


def position_exposures(
    positions: Iterable[ExposurePosition], nav: Decimal | None
) -> dict[str, PositionExposure]:
    rows = list(positions)
    if nav is not None and not nav.is_finite():
        raise ValueError("Exposure NAV must be finite or unavailable")
    if len({row.instrument_id for row in rows}) != len(rows):
        raise ValueError("Exposure positions must have unique instrument IDs")
    sector_values: dict[str, Decimal] = defaultdict(Decimal)
    unknown_sectors = set()
    for row in rows:
        if any(value is not None and not value.is_finite() for value in (row.base_value, row.beta)):
            raise ValueError("Exposure marks and beta must be finite or unavailable")
        if row.base_value is None:
            unknown_sectors.add(row.sector)
        else:
            sector_values[row.sector] += row.base_value
    results: dict[str, PositionExposure] = {}
    for row in rows:
        weight = row.base_value / nav if row.base_value is not None and nav else None
        sector_weight = (
            sector_values[row.sector] / nav if nav and row.sector not in unknown_sectors else None
        )
        results[row.instrument_id] = {
            "nav_weight": weight,
            "sector_weight": sector_weight,
            "beta_contribution": weight * row.beta
            if weight is not None and row.beta is not None
            else None,
        }
    return results
