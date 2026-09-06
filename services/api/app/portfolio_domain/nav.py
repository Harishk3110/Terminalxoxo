"""Decimal NAV identities and beginning-of-period cash-flow-adjusted returns."""

from collections.abc import Mapping, Sequence
from decimal import Decimal

from .money import ZERO, decimal

ASSET_BUCKETS = {"accrued_income", "receivables"}
LIABILITY_BUCKETS = {"payables", "accrued_fees", "other_liabilities"}


class NavCalculationService:
    @staticmethod
    def calculate(
        cash: Decimal,
        positions: Sequence[Decimal],
        balances: Mapping[str, Decimal],
        *,
        cash_components: Sequence[Decimal] | None = None,
    ) -> dict[str, Decimal]:
        unknown = set(balances) - ASSET_BUCKETS - LIABILITY_BUCKETS
        if unknown:
            raise ValueError(f"Unknown NAV balance bucket: {sorted(unknown)}")
        decimal(cash, "cash")
        components = tuple(cash_components) if cash_components is not None else (cash,)
        for value in components:
            decimal(value, "marked currency cash")
        if sum(components, ZERO) != cash:
            raise ValueError("Marked currency cash components must equal settled cash")
        for value in positions:
            decimal(value, "position market value")
        for bucket, value in balances.items():
            decimal(value, bucket, nonnegative=True)
        cash_assets = sum((max(value, ZERO) for value in components), ZERO)
        overdrafts = sum((max(-value, ZERO) for value in components), ZERO)
        long_assets = sum((max(value, ZERO) for value in positions), ZERO)
        short_liabilities = sum((max(-value, ZERO) for value in positions), ZERO)
        assets = sum((balances.get(key, ZERO) for key in sorted(ASSET_BUCKETS)), ZERO)
        recorded_liabilities = sum(
            (balances.get(key, ZERO) for key in sorted(LIABILITY_BUCKETS)), ZERO
        )
        invested = sum(positions, ZERO)
        gross_assets = cash_assets + long_assets + assets
        return {
            "nav": cash + invested + assets - recorded_liabilities,
            "cash": cash,
            "cash_assets": cash_assets,
            "cash_overdrafts": overdrafts,
            "market_value": invested,
            "long_market_value": long_assets,
            "short_liabilities": short_liabilities,
            "gross_asset_value": gross_assets,
            "accrued_income": balances.get("accrued_income", ZERO),
            "receivables": balances.get("receivables", ZERO),
            "payables": balances.get("payables", ZERO),
            "accrued_fees": balances.get("accrued_fees", ZERO),
            "other_liabilities": balances.get("other_liabilities", ZERO),
            "liabilities": recorded_liabilities + overdrafts + short_liabilities,
        }


nav_total = NavCalculationService.calculate


def daily_performance(
    opening: Decimal, closing: Decimal, flows: Decimal
) -> tuple[Decimal, Decimal | None]:
    for name, value in (("opening NAV", opening), ("closing NAV", closing), ("flows", flows)):
        decimal(value, name)
    pnl = closing - opening - flows
    denominator = opening + flows
    return pnl, (pnl / denominator if denominator > ZERO else None)
