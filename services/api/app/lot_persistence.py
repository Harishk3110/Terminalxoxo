"""Persist valuation-owned lot evidence without altering earlier runs."""

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from .ledger_models import PositionLot, PositionLotMatch


def persist_lots(
    session: Session,
    run_id: str,
    lots: list[dict[str, Any]],
    matches: list[dict[str, Any]],
) -> None:
    for lot in lots:
        session.add(
            PositionLot(
                valuation_run_id=run_id,
                instrument_id=lot["instrument_id"],
                opening_transaction_id=lot["entry_id"],
                lot_key=lot["id"],
                opened=date.fromisoformat(lot["opened"]),
                direction=lot["direction"],
                quantity=Decimal(lot["quantity"]),
                native_basis=Decimal(lot["native_basis"]),
                base_basis=Decimal(lot["base_basis"]),
                multiplier=Decimal(lot["multiplier"]),
            )
        )
    for match in matches:
        session.add(
            PositionLotMatch(
                valuation_run_id=run_id,
                instrument_id=match["instrument_id"],
                opening_transaction_id=match["opening_entry_id"],
                closing_transaction_id=match["closing_entry_id"],
                lot_key=match["lot_id"],
                direction=match["direction"],
                closed=date.fromisoformat(match["closed"]),
                quantity=Decimal(match["quantity"]),
                native_basis=Decimal(match["native_basis"]),
                base_basis=Decimal(match["base_basis"]),
                native_proceeds=Decimal(match["native_proceeds"]),
                base_proceeds=Decimal(match["base_proceeds"]),
                realised_native=Decimal(match["realised_native"]),
                realised_base=Decimal(match["realised_base"]),
            )
        )
