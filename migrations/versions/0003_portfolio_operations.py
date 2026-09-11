"""Add portfolio-first accounting, provenance, trade and file-agent records."""

from alembic import op
from app import models

revision = "0003_portfolio_operations"
down_revision = "0002_terminal_workspace"
branch_labels = None
depends_on = None

NAMES = {
    "portfolio_profiles",
    "transaction_details",
    "portfolio_balance_adjustments",
    "market_observations",
    "fx_observations",
    "source_precedence_rules",
    "portfolio_valuation_runs",
    "position_valuations",
    "trade_events",
    "trade_reviews",
    "trade_risk_snapshots",
    "broker_account_snapshots",
    "portfolio_reconciliation_breaks",
    "mapping_profiles",
    "local_agents",
    "local_agent_pairings",
    "external_files",
    "file_hashes",
    "research_candidates",
}


def upgrade():
    for table in models.Base.metadata.sorted_tables:
        if table.name in NAMES:
            table.create(op.get_bind(), checkfirst=True)


def downgrade():
    for table in reversed(models.Base.metadata.sorted_tables):
        if table.name in NAMES:
            table.drop(op.get_bind(), checkfirst=True)
