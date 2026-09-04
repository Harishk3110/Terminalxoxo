# Data Model

Version 0.1 uses deterministic in-code demo fixtures and JSON schema fixtures. The persistent model will be backed by PostgreSQL for operational records, Redis for transient state, object storage for raw and curated files, Parquet for analytical datasets, and DuckDB for local analytical queries.

Core model groups:

- Public content.
- Security master.
- Prices and corporate actions.
- Fundamentals and estimates.
- Portfolio ledger and positions.
- Broker snapshots.
- Risk and performance snapshots.
- Research, theses, attachments, and publishing approvals.
- Provider credentials metadata and connection state.
- Jobs, audit logs, alerts, and health events.
