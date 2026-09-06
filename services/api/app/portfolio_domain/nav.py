"""Decimal NAV identities and beginning-of-period cash-flow-adjusted returns."""

from decimal import Decimal

from .money import ZERO, decimal

ASSET_BUCKETS = {"accrued_income", "receivables"}
LIABILITY_BUCKETS = {"payables", "accrued_fees", "other_liabilities"}


def nav_total(
    cash: Decimal, positions: list[Decimal], balances: dict[str, Decimal]
) -> dict[str, Decimal]:
    unknown = set(balances) - ASSET_BUCKETS - LIABILITY_BUCKETS
    if unknown:
        raise ValueError(f"Unknown NAV balance bucket: {sorted(unknown)}")
    decimal(cash, "cash")
    for value in positions:
        decimal(value, "position market value")
    for bucket, value in balances.items():
        decimal(value, bucket, nonnegative=True)
    assets = sum((balances.get(key, ZERO) for key in ASSET_BUCKETS), ZERO)
    liabilities = sum((balances.get(key, ZERO) for key in LIABILITY_BUCKETS), ZERO)
    invested = sum(positions, ZERO)
    gross_assets = max(cash, ZERO) + sum((max(value, ZERO) for value in positions), ZERO) + assets
    return {
        "nav": cash + invested + assets - liabilities,
        "cash": cash,
        "market_value": invested,
        "gross_asset_value": gross_assets,
        "accrued_income": balances.get("accrued_income", ZERO),
        "receivables": balances.get("receivables", ZERO),
        "liabilities": liabilities,
        **balances,
    }


def daily_performance(
    opening: Decimal, closing: Decimal, flows: Decimal
) -> tuple[Decimal, Decimal | None]:
    for name, value in (("opening NAV", opening), ("closing NAV", closing), ("flows", flows)):
        decimal(value, name)
    pnl = closing - opening - flows
    denominator = opening + flows
    return pnl, (pnl / denominator if denominator > ZERO else None)
