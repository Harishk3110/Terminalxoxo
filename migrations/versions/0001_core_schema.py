"""Create core KnK Capital Terminal schema.

Revision ID: 0001_core_schema
Revises:
Create Date: 2026-09-05
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic import op

ROOT = Path(__file__).resolve().parents[2]
API_ROOT = ROOT / "services" / "api"
for path in (ROOT, API_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app.models import Base  # noqa: E402

revision = "0001_core_schema"
down_revision = None
branch_labels = None
depends_on = None

# Freeze table ownership so later revisions are not created ahead of their migration.
BASELINE_TABLES = {
    "users",
    "user_sessions",
    "totp_settings",
    "recovery_codes",
    "login_attempts",
    "currencies",
    "exchanges",
    "benchmarks",
    "instruments",
    "instrument_identifiers",
    "provider_instrument_mappings",
    "provider_connections",
    "provider_health_snapshots",
    "provider_request_logs",
    "provider_rate_limit_states",
    "raw_objects",
    "macro_series",
    "macro_observations",
    "macro_releases",
    "macro_vintages",
    "price_bars",
    "latest_quotes",
    "fx_rates",
    "corporate_actions",
    "datasets",
    "dataset_versions",
    "dataset_columns",
    "dataset_lineage",
    "uploaded_files",
    "ingestion_jobs",
    "ingestion_job_runs",
    "data_quality_issues",
    "quarantine_records",
    "portfolios",
    "portfolio_accounts",
    "portfolio_transactions",
    "portfolio_positions",
    "portfolio_cash_balances",
    "cash_flows",
    "nav_snapshots",
    "daily_returns",
    "benchmark_returns",
    "target_allocations",
    "performance_snapshots",
    "risk_policies",
    "risk_limits",
    "risk_snapshots",
    "risk_breaches",
    "stress_scenarios",
    "stress_results",
    "hedge_instruments",
    "hedge_recommendations",
    "hedge_recommendation_items",
    "strategy_definitions",
    "strategy_versions",
    "strategy_parameters",
    "backtest_runs",
    "backtest_metrics",
    "backtest_equity_curve",
    "backtest_positions",
    "backtest_trades",
    "signals",
    "factor_definitions",
    "factor_runs",
    "factor_values",
    "watchlists",
    "watchlist_items",
    "research_notes",
    "investment_theses",
    "thesis_sources",
    "thesis_attachments",
    "decision_journal",
    "alerts",
    "alert_deliveries",
    "audit_logs",
    "system_health_snapshots",
    "workspaces",
    "workspace_tabs",
    "favourite_functions",
    "recent_commands",
    "workspace_states",
    "analysis_runs",
    "fundamental_snapshots",
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


def upgrade() -> None:
    bind = op.get_bind()
    tables = [table for table in Base.metadata.sorted_tables if table.name in BASELINE_TABLES]
    Base.metadata.create_all(bind=bind, tables=tables)


def downgrade() -> None:
    bind = op.get_bind()
    tables = [table for table in Base.metadata.sorted_tables if table.name in BASELINE_TABLES]
    Base.metadata.drop_all(bind=bind, tables=tables)
