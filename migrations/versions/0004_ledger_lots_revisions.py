"""Add immutable lot snapshots and versioned ledger corrections."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.schema import SchemaItem

revision = "0004_ledger_lots_revisions"
down_revision = "0003_portfolio_operations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def identity_columns() -> list[SchemaItem]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def lot_columns() -> list[SchemaItem]:
    return [
        *identity_columns(),
        sa.Column(
            "valuation_run_id",
            sa.String(36),
            sa.ForeignKey("portfolio_valuation_runs.id"),
            nullable=False,
        ),
        sa.Column("instrument_id", sa.String(36), sa.ForeignKey("instruments.id"), nullable=False),
        sa.Column(
            "opening_transaction_id",
            sa.String(36),
            sa.ForeignKey("portfolio_transactions.id"),
            nullable=False,
        ),
        sa.Column("lot_key", sa.String(36), nullable=False),
        sa.Column("direction", sa.String(8), nullable=False),
        sa.Column("quantity", sa.Numeric(38, 16), nullable=False),
        sa.Column("native_basis", sa.Numeric(38, 16), nullable=False),
        sa.Column("base_basis", sa.Numeric(38, 16), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "transaction_revisions",
        *identity_columns(),
        sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column(
            "transaction_id",
            sa.String(36),
            sa.ForeignKey("portfolio_transactions.id"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id")),
        sa.Column("before", sa.JSON(), nullable=False),
        sa.Column("after", sa.JSON(), nullable=False),
        sa.UniqueConstraint("transaction_id", "version", name="uq_transaction_revision_version"),
        sa.CheckConstraint("version >= 2", name="ck_transaction_revision_version"),
        sa.CheckConstraint("action IN ('AMEND', 'VOID')", name="ck_transaction_revision_action"),
    )
    op.create_index(
        "ix_transaction_revision_portfolio",
        "transaction_revisions",
        ["portfolio_id", "transaction_id", "version"],
    )
    op.create_table(
        "position_lots",
        *lot_columns(),
        sa.Column("opened", sa.Date(), nullable=False),
        sa.Column("multiplier", sa.Numeric(24, 8), nullable=False),
        sa.UniqueConstraint("valuation_run_id", "lot_key", name="uq_position_lot_run_key"),
        sa.CheckConstraint("quantity >= 0", name="ck_position_lot_quantity"),
        sa.CheckConstraint("multiplier > 0", name="ck_position_lot_multiplier"),
        sa.CheckConstraint("direction IN ('LONG', 'SHORT')", name="ck_position_lot_direction"),
    )
    op.create_index(
        "ix_position_lot_run_instrument", "position_lots", ["valuation_run_id", "instrument_id"]
    )
    op.create_table(
        "position_lot_matches",
        *lot_columns(),
        sa.Column(
            "closing_transaction_id",
            sa.String(36),
            sa.ForeignKey("portfolio_transactions.id"),
            nullable=False,
        ),
        sa.Column("closed", sa.Date(), nullable=False),
        sa.Column("native_proceeds", sa.Numeric(38, 16), nullable=False),
        sa.Column("base_proceeds", sa.Numeric(38, 16), nullable=False),
        sa.Column("realised_native", sa.Numeric(38, 16), nullable=False),
        sa.Column("realised_base", sa.Numeric(38, 16), nullable=False),
        sa.UniqueConstraint(
            "valuation_run_id", "lot_key", "closing_transaction_id", name="uq_lot_match_run_close"
        ),
        sa.CheckConstraint("quantity > 0", name="ck_lot_match_quantity"),
        sa.CheckConstraint("direction IN ('LONG', 'SHORT')", name="ck_lot_match_direction"),
    )
    op.create_index(
        "ix_lot_match_run_instrument", "position_lot_matches", ["valuation_run_id", "instrument_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_lot_match_run_instrument", table_name="position_lot_matches")
    op.drop_table("position_lot_matches")
    op.drop_index("ix_position_lot_run_instrument", table_name="position_lots")
    op.drop_table("position_lots")
    op.drop_index("ix_transaction_revision_portfolio", table_name="transaction_revisions")
    op.drop_table("transaction_revisions")
