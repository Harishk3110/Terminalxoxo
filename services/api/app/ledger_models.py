"""Immutable replay snapshots and append-only transaction revision history."""

from datetime import date
from decimal import Decimal

from pydantic import JsonValue
from sqlalchemy import (
    JSON,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .schema import Base, IdMixin


class TransactionRevision(IdMixin, Base):
    __tablename__ = "transaction_revisions"
    portfolio_id: Mapped[str] = mapped_column(ForeignKey("portfolios.id"), nullable=False)
    transaction_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_transactions.id"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    before: Mapped[dict[str, JsonValue]] = mapped_column(JSON, nullable=False)
    after: Mapped[dict[str, JsonValue]] = mapped_column(JSON, nullable=False)
    __table_args__ = (
        UniqueConstraint("transaction_id", "version", name="uq_transaction_revision_version"),
        CheckConstraint("version >= 2", name="ck_transaction_revision_version"),
        CheckConstraint("action IN ('AMEND', 'VOID')", name="ck_transaction_revision_action"),
        Index("ix_transaction_revision_portfolio", "portfolio_id", "transaction_id", "version"),
    )


class PositionLot(IdMixin, Base):
    __tablename__ = "position_lots"
    valuation_run_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_valuation_runs.id"), nullable=False
    )
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    opening_transaction_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_transactions.id"), nullable=False
    )
    lot_key: Mapped[str] = mapped_column(String(36), nullable=False)
    opened: Mapped[date] = mapped_column(Date, nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    native_basis: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    base_basis: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    multiplier: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    __table_args__ = (
        UniqueConstraint("valuation_run_id", "lot_key", name="uq_position_lot_run_key"),
        CheckConstraint("quantity >= 0", name="ck_position_lot_quantity"),
        CheckConstraint("multiplier > 0", name="ck_position_lot_multiplier"),
        CheckConstraint("direction IN ('LONG', 'SHORT')", name="ck_position_lot_direction"),
        Index("ix_position_lot_run_instrument", "valuation_run_id", "instrument_id"),
    )


class PositionLotMatch(IdMixin, Base):
    __tablename__ = "position_lot_matches"
    valuation_run_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_valuation_runs.id"), nullable=False
    )
    instrument_id: Mapped[str] = mapped_column(ForeignKey("instruments.id"), nullable=False)
    opening_transaction_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_transactions.id"), nullable=False
    )
    closing_transaction_id: Mapped[str] = mapped_column(
        ForeignKey("portfolio_transactions.id"), nullable=False
    )
    lot_key: Mapped[str] = mapped_column(String(36), nullable=False)
    direction: Mapped[str] = mapped_column(String(8), nullable=False)
    closed: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    native_basis: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    base_basis: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    native_proceeds: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    base_proceeds: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    realised_native: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    realised_base: Mapped[Decimal] = mapped_column(Numeric(38, 16), nullable=False)
    __table_args__ = (
        UniqueConstraint(
            "valuation_run_id", "lot_key", "closing_transaction_id", name="uq_lot_match_run_close"
        ),
        CheckConstraint("quantity > 0", name="ck_lot_match_quantity"),
        CheckConstraint("direction IN ('LONG', 'SHORT')", name="ck_lot_match_direction"),
        Index("ix_lot_match_run_instrument", "valuation_run_id", "instrument_id"),
    )
