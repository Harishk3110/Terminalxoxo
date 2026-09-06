"""Adapt valuation records into the typed exposure calculation without rounding inputs."""

from collections.abc import Mapping, Sequence
from decimal import Decimal
from typing import Any

from .portfolio_domain.exposure import ExposureItem, PortfolioExposureService


def exposure_service(
    positions: Sequence[Mapping[str, Any]],
    cash: Sequence[Mapping[str, Any]],
    balances: Sequence[Mapping[str, Any]],
    nav: Decimal | None,
) -> PortfolioExposureService:
    items = []
    for row in positions:
        value = row.get("market_value_base_exact", row.get("market_value"))
        items.append(
            ExposureItem(
                identifier=str(row["instrument_id"]),
                kind="POSITION",
                currency=str(row["currency"]),
                value=Decimal(value) if value is not None else None,
                asset_class=row.get("asset_class") or "Unclassified",
                sector=row.get("sector"),
                country=row.get("country"),
                stale=bool(
                    row["price_provenance"].get("stale") or row["fx_provenance"].get("stale")
                ),
                price_available=row["market_price"] is not None,
                fx_available=row["fx_rate"] is not None,
            )
        )
    for row in cash:
        value = row.get("base_value_exact", row.get("base_value"))
        items.append(
            ExposureItem(
                identifier=str(row["currency"]),
                kind="CASH",
                currency=str(row["currency"]),
                value=Decimal(value) if value is not None else None,
                asset_class="Cash",
                stale=bool(row.get("fx_provenance", {}).get("stale")),
                fx_available=row["fx_rate"] is not None,
            )
        )
    for row in balances:
        value = row["base_value"]
        items.append(
            ExposureItem(
                identifier=str(row["bucket"]) + ":" + str(row["currency"]),
                kind="BALANCE",
                currency=str(row["currency"]),
                value=Decimal(value) if value is not None else None,
                asset_class="Accrual"
                if row["bucket"] in {"accrued_income", "receivables"}
                else "Liability",
                stale=bool(row["fx_provenance"].get("stale")),
                fx_available=row["fx_rate"] is not None,
            )
        )
    return PortfolioExposureService(items, nav)
