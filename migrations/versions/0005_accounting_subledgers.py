"""Add immutable capital, income, charge and outstanding balance components."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.schema import SchemaItem

revision = "0005_accounting_subledgers"
down_revision = "0004_ledger_lots_revisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLES = (
    (
        "capital_flows",
        "capital_flow",
        ("DEPOSIT", "WITHDRAWAL", "TRANSFER_IN", "TRANSFER_OUT"),
        False,
    ),
    ("portfolio_income", "portfolio_income", ("DIVIDEND", "INTEREST"), False),
    ("portfolio_fees", "portfolio_fee", ("COMMISSION", "FEE", "TAX"), False),
    ("portfolio_accruals", "portfolio_accrual", ("accrued_income", "receivables"), True),
    (
        "portfolio_liabilities",
        "portfolio_liability",
        ("payables", "accrued_fees", "other_liabilities"),
        True,
    ),
)


def component_columns() -> list[SchemaItem]:
    return [
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "valuation_run_id",
            sa.String(36),
            sa.ForeignKey("portfolio_valuation_runs.id"),
            nullable=False,
        ),
        sa.Column("portfolio_id", sa.String(36), sa.ForeignKey("portfolios.id"), nullable=False),
        sa.Column("component_key", sa.String(180), nullable=False),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("portfolio_transactions.id")),
        sa.Column("account_id", sa.String(36), sa.ForeignKey("portfolio_accounts.id")),
        sa.Column("instrument_id", sa.String(36), sa.ForeignKey("instruments.id")),
        sa.Column(
            "adjustment_id", sa.String(36), sa.ForeignKey("portfolio_balance_adjustments.id")
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("settlement_date", sa.Date()),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("native_amount", sa.Numeric(38, 16), nullable=False),
        sa.Column("fx_rate", sa.Numeric(38, 16)),
        sa.Column("base_amount", sa.Numeric(38, 16)),
        sa.Column("capitalized_native", sa.Numeric(38, 16), nullable=False),
        sa.Column("capitalized_base", sa.Numeric(38, 16)),
        sa.Column("payload", sa.JSON(), nullable=False),
    ]


def upgrade() -> None:
    for table, name, kinds, outstanding in TABLES:
        permitted = ", ".join(f"'{kind}'" for kind in kinds)
        source = (
            "(transaction_id IS NOT NULL AND adjustment_id IS NULL) OR "
            "(transaction_id IS NULL AND adjustment_id IS NOT NULL)"
            if outstanding
            else "transaction_id IS NOT NULL AND adjustment_id IS NULL AND fx_rate IS NOT NULL AND base_amount IS NOT NULL"
        )
        extra: list[sa.CheckConstraint] = []
        if table == "portfolio_income":
            extra.append(
                sa.CheckConstraint("native_amount > 0", name="ck_portfolio_income_positive")
            )
        if table == "portfolio_fees":
            extra.extend(
                [
                    sa.CheckConstraint(
                        "native_amount > 0 AND capitalized_native <= native_amount",
                        name="ck_portfolio_fee_amount",
                    ),
                    sa.CheckConstraint(
                        "kind != 'TAX' OR capitalized_native = 0", name="ck_portfolio_fee_tax"
                    ),
                ]
            )
        op.create_table(
            table,
            *component_columns(),
            sa.UniqueConstraint("valuation_run_id", "component_key", name=f"uq_{name}_run_key"),
            sa.CheckConstraint(f"kind IN ({permitted})", name=f"ck_{name}_kind"),
            sa.CheckConstraint("fx_rate IS NULL OR fx_rate > 0", name=f"ck_{name}_fx"),
            sa.CheckConstraint(
                "settlement_date IS NULL OR settlement_date >= effective_date",
                name=f"ck_{name}_settlement",
            ),
            sa.CheckConstraint("capitalized_native >= 0", name=f"ck_{name}_capitalized"),
            sa.CheckConstraint(
                "(fx_rate IS NULL AND base_amount IS NULL AND capitalized_base IS NULL) OR "
                "(fx_rate IS NOT NULL AND base_amount IS NOT NULL AND capitalized_base IS NOT NULL)",
                name=f"ck_{name}_valuation",
            ),
            sa.CheckConstraint(source, name=f"ck_{name}_source"),
            *extra,
        )
        op.create_index(f"ix_{name}_portfolio_date", table, ["portfolio_id", "effective_date"])


def downgrade() -> None:
    for table, name, _, _ in reversed(TABLES):
        op.drop_index(f"ix_{name}_portfolio_date", table_name=table)
        op.drop_table(table)
