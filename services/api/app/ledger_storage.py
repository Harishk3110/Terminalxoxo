"""Shared driver boundary for immutable source records and audited corrections."""

from collections.abc import Callable, Mapping
from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.engine import Dialect
from sqlalchemy.orm import Session

from .portfolio_domain.money import money, stored_decimal
from .portfolio_domain.types import Entry


def validate_storage(session: Session, values: Mapping[str, Decimal]) -> None:
    dialect = session.get_bind().dialect
    if dialect.name != "sqlite":
        return
    # SQLAlchemy's dialect hook is unannotated; its input here is always a float.
    factory: Callable[[Dialect, object], Callable[[float], Decimal] | None] = Numeric(
        24, 8
    ).result_processor
    processor = factory(dialect, None)
    if processor is not None:
        for name, value in values.items():
            if processor(float(value)) != value:
                raise ValueError(
                    f"{name} cannot round-trip through local SQLite storage at eight decimal places"
                )


def validate_corrected_storage(session: Session, entry: Entry) -> None:
    projected_base = stored_decimal(
        money(entry.gross * entry.fx, 8), "corrected stored base value", nonnegative=True
    )
    validate_storage(
        session,
        {
            "corrected quantity": entry.quantity,
            "corrected price": entry.price,
            "corrected fee": entry.fee,
            "corrected commission": entry.commission,
            "corrected tax": entry.tax,
            "corrected multiplier": entry.multiplier,
            "corrected gross amount": entry.gross,
            "corrected transaction FX": entry.fx,
            "corrected stored base value": projected_base,
        },
    )
