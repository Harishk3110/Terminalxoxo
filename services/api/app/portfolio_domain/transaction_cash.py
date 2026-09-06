"""Project transaction cash effects from actual replay movements, including FX legs."""

from collections import defaultdict
from collections.abc import Iterable
from decimal import Decimal
from typing import Any

from .cash import CashMovement
from .money import ZERO
from .types import Entry


def enrich_cash_effects(
    payloads: list[dict[str, Any]],
    entries: Iterable[Entry],
    movements: Iterable[CashMovement],
) -> None:
    effective = {entry.id for entry in entries}
    native: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    base: dict[str, dict[str, Decimal]] = defaultdict(lambda: defaultdict(Decimal))
    for movement in movements:
        native[movement.transaction_id][movement.currency] += movement.amount
        base[movement.transaction_id][movement.currency] += movement.amount * movement.fx
    for payload in payloads:
        identifier, currency = payload["id"], payload["currency"]
        payload["net_amount_basis"] = "SOURCE-CURRENCY ECONOMIC CASH IMPACT"
        if identifier not in effective:
            payload.update(
                {
                    "net_amount": None,
                    "net_base_value": None,
                    "net_cash_base": None,
                    "net_cash_by_currency": [],
                    "cash_effect_state": "NOT_REPLAYED",
                }
            )
            continue
        native_amounts = native.get(identifier, {})
        base_amounts = base.get(identifier, {})
        payload.update(
            {
                "net_amount": str(native_amounts.get(currency, ZERO)),
                "net_base_value": str(base_amounts.get(currency, ZERO)),
                "net_cash_base": str(sum(base_amounts.values(), ZERO)),
                "net_cash_by_currency": [
                    {
                        "currency": code,
                        "amount": str(amount),
                        "base_amount": str(base_amounts[code]),
                    }
                    for code, amount in sorted(native_amounts.items())
                ],
                "cash_effect_state": "REPLAYED",
            }
        )
