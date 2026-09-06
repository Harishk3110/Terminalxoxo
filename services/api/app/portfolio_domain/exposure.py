"""Marked exposures retain missing groups and separate positions, cash and balances."""

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from .money import ZERO, money

ExposureKind = Literal["POSITION", "CASH", "BALANCE"]
DIMENSIONS = ("sector", "country", "currency", "asset_class", "industry")


@dataclass(frozen=True)
class ExposureItem:
    identifier: str
    kind: ExposureKind
    currency: str
    value: Decimal | None
    asset_class: str
    sector: str | None = None
    country: str | None = None
    stale: bool = False
    price_available: bool = True
    fx_available: bool = True
    industry: str | None = None

    def __post_init__(self) -> None:
        if not self.identifier or self.kind not in {"POSITION", "CASH", "BALANCE"}:
            raise ValueError("Exposure requires an identifier and supported component kind")
        if not self.currency or len(self.currency) != 3:
            raise ValueError("Exposure requires a three-letter currency")
        if self.value is not None and not self.value.is_finite():
            raise ValueError("Exposure value must be finite or unavailable")

    def group(self, dimension: str) -> str | None:
        if dimension not in DIMENSIONS:
            raise ValueError("Unsupported exposure dimension")
        if self.kind != "POSITION" and dimension in {"sector", "country", "industry"}:
            return None
        label = getattr(self, dimension)
        return str(label).strip() if label and str(label).strip() else "Unclassified"


@dataclass(frozen=True)
class ExposureGroup:
    name: str
    items: tuple[ExposureItem, ...]
    nav: Decimal | None

    @property
    def missing_count(self) -> int:
        return sum(item.value is None for item in self.items)

    @property
    def known_value(self) -> Decimal:
        return sum((item.value for item in self.items if item.value is not None), ZERO)

    @property
    def net_value(self) -> Decimal | None:
        return None if self.missing_count else self.known_value

    @property
    def gross_value(self) -> Decimal | None:
        if self.missing_count:
            return None
        return sum((abs(item.value) for item in self.items if item.value is not None), ZERO)

    def component(self, kind: ExposureKind, sign: int | None = None) -> Decimal | None:
        rows = [item for item in self.items if item.kind == kind]
        if any(item.value is None for item in rows):
            return None
        return sum(
            (
                item.value
                for item in rows
                if item.value is not None
                and (sign is None or (item.value >= ZERO if sign == 1 else item.value < ZERO))
            ),
            ZERO,
        )

    def payload(self) -> dict[str, Any]:
        net, gross = self.net_value, self.gross_value
        return {
            "name": self.name,
            "value": money(net) if net is not None else None,
            "net_value": net,
            "gross_value": gross,
            "known_value": self.known_value,
            "long_value": self.component("POSITION", 1),
            "short_value": self.component("POSITION", -1),
            "cash_value": self.component("CASH"),
            "balance_value": self.component("BALANCE"),
            "weight": net / self.nav if net is not None and self.nav else None,
            "gross_weight": gross / abs(self.nav) if gross is not None and self.nav else None,
            "state": "INCOMPLETE" if self.missing_count else "AVAILABLE",
            "item_count": len(self.items),
            "position_count": sum(item.kind == "POSITION" for item in self.items),
            "missing_count": self.missing_count,
            "stale_count": sum(item.stale for item in self.items),
        }


class PortfolioExposureService:
    def __init__(self, items: Iterable[ExposureItem], nav: Decimal | None):
        self.items = tuple(items)
        self.nav = nav
        if nav is not None and not nav.is_finite():
            raise ValueError("Exposure NAV must be finite or unavailable")
        keys = [(item.kind, item.identifier) for item in self.items]
        if len(keys) != len(set(keys)):
            raise ValueError("Exposure components must not be duplicated")

    def groups(self) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        for dimension in DIMENSIONS:
            grouped: dict[str, list[ExposureItem]] = defaultdict(list)
            for item in self.items:
                name = item.group(dimension)
                if name is not None:
                    grouped[name].append(item)
            rows = [ExposureGroup(name, tuple(items), self.nav) for name, items in grouped.items()]
            rows.sort(key=lambda row: (-abs(row.known_value), row.name))
            result[dimension] = [row.payload() for row in rows]
        return result

    def freshness(self) -> dict[str, Any]:
        stale_by_kind = {
            kind: sum(
                (
                    abs(item.value)
                    for item in self.items
                    if item.kind == kind and item.stale and item.value is not None
                ),
                ZERO,
            )
            for kind in ("POSITION", "CASH", "BALANCE")
        }
        stale_value = sum(stale_by_kind.values(), ZERO)
        missing = sum(item.value is None for item in self.items)
        positions = [item for item in self.items if item.kind == "POSITION"]
        cash = [item for item in self.items if item.kind == "CASH"]
        return {
            "stale_market_value": money(stale_by_kind["POSITION"]),
            "stale_cash_value": money(stale_by_kind["CASH"]),
            "stale_balance_value": money(stale_by_kind["BALANCE"]),
            "stale_total_value": stale_value,
            "stale_nav_pct": stale_value / abs(self.nav)
            if self.nav is not None and self.nav and not missing
            else None,
            "known_marked_value": sum(
                (abs(item.value) for item in self.items if item.value is not None), ZERO
            ),
            "state": "INCOMPLETE" if missing else "AVAILABLE",
            "unavailable_items": missing,
            "stale_items": sum(item.stale for item in self.items),
            "item_count": len(self.items),
            "price_coverage_pct": sum(
                item.price_available and item.fx_available for item in positions
            )
            / len(positions)
            * 100
            if positions
            else 100,
            "cash_fx_coverage_pct": sum(item.fx_available for item in cash) / len(cash) * 100
            if cash
            else 100,
            "methodology": "Absolute marked positions, economic cash and net outstanding balance buckets; stale components counted once; missing marks are not zero-filled; percentage uses absolute NAV and is not capped at 100%",
        }
