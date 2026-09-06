# Data Model

Current migration: `0001_core_schema`

Primary model file: `services/api/app/models.py`

## Implemented Table Groups

- Auth: `users`, `user_sessions`, `totp_settings`, `recovery_codes`, `login_attempts`.
- Reference: `currencies`, `exchanges`, `benchmarks`, `instruments`, `instrument_identifiers`, `provider_instrument_mappings`.
- Providers: `provider_connections`, `provider_health_snapshots`, `provider_request_logs`, `provider_rate_limit_states`.
- Raw objects: `raw_objects`.
- Macro: `macro_series`, `macro_observations`, `macro_releases`, `macro_vintages`.
- Market data: `price_bars`, `latest_quotes`, `fx_rates`, `corporate_actions`.
- Data operations: `datasets`, `dataset_versions`, `dataset_columns`, `dataset_lineage`, `uploaded_files`, `ingestion_jobs`, `ingestion_job_runs`, `data_quality_issues`, `quarantine_records`.
- Portfolio: `portfolios`, `portfolio_accounts`, `portfolio_transactions`, `portfolio_positions`, `portfolio_cash_balances`, `cash_flows`, `nav_snapshots`, `daily_returns`, `benchmark_returns`, `target_allocations`.
- Performance/risk/hedge: `performance_snapshots`, `risk_policies`, `risk_limits`, `risk_snapshots`, `risk_breaches`, `stress_scenarios`, `stress_results`, `hedge_instruments`, `hedge_recommendations`, `hedge_recommendation_items`.
- Quant: `strategy_definitions`, `strategy_versions`, `strategy_parameters`, `backtest_runs`, `backtest_metrics`, `backtest_equity_curve`, `backtest_positions`, `backtest_trades`, `signals`, `factor_definitions`, `factor_runs`, `factor_values`.
- Research: `watchlists`, `watchlist_items`, `research_notes`, `investment_theses`, `thesis_sources`, `thesis_attachments`, `decision_journal`.
- Operations: `alerts`, `alert_deliveries`, `audit_logs`, `system_health_snapshots`, `workspaces`, `workspace_tabs`, `favourite_functions`, `recent_commands`.

## Modeling Rules

- Internal identifiers are immutable UUID strings.
- Foreign keys connect child records to parent tables.
- Common date/instrument/portfolio queries have indexes or unique constraints.
- Authoritative financial values use SQLAlchemy `Numeric` and Python `Decimal`.
- Provider/source, quality, raw object, and timestamp fields preserve lineage where implemented.
- Secrets are not stored in provider tables; runtime credentials are loaded from environment variables.

## Local Storage

Local development uses SQLite by default. Docker Compose requires a PostgreSQL
`DATABASE_URL` in the ignored `.env` file, using the `postgres` service hostname,
database `knk_terminal` and user `knk`. Its password must match `POSTGRES_PASSWORD`;
URL-encode credentials in the URL. No database credential is committed.
