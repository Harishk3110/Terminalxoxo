# TASKS

## Directive Tracking

- [x] Continue in the current repository, branch, and remote.
- [x] Run repository audit and create `docs/GAP_AUDIT.md`.
- [x] Replace vague task/status tracking with executable status files.
- [x] Create `docs/CORE_ACCEPTANCE.md`.
- [x] Add real SQLAlchemy 2 persistence models for auth, reference, providers, macro, market data, data operations, portfolio, risk, quant, research, and operations.
- [x] Add Alembic migration revision `0001_core_schema`.
- [x] Verify clean Alembic upgrade/downgrade/upgrade.
- [x] Seed deterministic demo data through raw object, normalization, DB, service, API, frontend path.
- [x] Seed 20 instruments, US equities, ETFs, SGX instrument, USD/SGD FX, benchmark-like index, 10 years daily prices, intraday bars, macro fixtures, SGD 70,000 portfolio, transactions, cash, dividends, fees, research, strategies, jobs, alerts, backtest, stress, hedge, data-quality issue, and system-health snapshots.
- [x] Implement provider interfaces and `ProviderRegistry`.
- [x] Implement FRED provider adapter using official FRED API shape with no hardcoded credential.
- [x] Implement raw-response preservation through object storage abstraction.
- [x] Implement macro APIs and API-backed macro dashboard UI.
- [x] Implement portfolio ledger, manual transaction route, cash/position/NAV/P&L recalculation, and API-backed UI.
- [x] Implement performance, risk, stress, and hedge calculation services and API-backed UI.
- [x] Implement CSV/JSON upload, object storage, schema inference, dataset versions, and data catalogue UI.
- [x] Implement strategy persistence and deterministic moving-average backtest persistence.
- [x] Implement Excel workbook generation for portfolio, risk, backtest, and macro exports.
- [x] Implement TradingView Pine Script export for moving-average crossover.
- [x] Implement security guard that fails on forbidden broker execution method names.
- [x] Implement public/private API separation test.
- [x] Implement meaningful Playwright smoke over API-backed terminal pages.
- [x] Add Docker Compose services for Postgres, Redis, MinIO, API, workers, report engine, broker agent, Prefect, public web, terminal web, Prometheus, and Grafana.
- [x] Add health checks/restart policies for long-running Compose services.
- [x] Validate Docker Compose config.
- [ ] Validate `docker compose build` with Docker Desktop Linux engine running.
- [ ] Validate `docker compose up --build` startup and service health with Docker Desktop Linux engine running.
- [ ] Run optional live FRED smoke after a real `FRED_API_KEY` is configured.
- [ ] Add Ruff/mypy or equivalent backend lint/typecheck gates.
- [ ] Expand coverage to the directive's target percentages for portfolio, performance, risk, hedge, backtesting, and provider-normalization modules.
- [ ] Replace remaining echo-only package test scripts with substantive unit tests.
- [ ] Add full administrator login/TOTP browser journey coverage.
- [ ] Add asynchronous FRED worker jobs and daily schedule execution beyond the synchronous API backfill path.
- [ ] Add XLSX/Parquet worker-side upload parsing beyond current API CSV/JSON support.
- [ ] Add Grafana dashboard JSON provisioning for all named dashboards.

## Milestone State

- [x] Milestone A audit/infrastructure: implemented and non-Docker validations passed; Docker engine blocked.
- [x] Milestone B FRED/macro: implemented with mocked tests; live credential path unrun.
- [x] Milestone C portfolio: implemented with ledger and UI.
- [x] Milestone D performance/risk/hedge: implemented with deterministic calculations and UI.
- [x] Milestone E data drop: implemented for CSV/JSON API flow.
- [x] Milestone F quant/backtesting: implemented deterministic moving-average persisted run.
- [x] Milestone G reports/TradingView: implemented XLSX and Pine export.
- [x] Milestone H monitoring/hardening: health/metrics/security scan implemented; Grafana dashboards still incomplete.
- [ ] Milestone I final acceptance: blocked on Docker engine and expanded coverage targets.
