# TASKS

## Terminal UI V2 / 2026-09-06

- [x] Audit the stacked layout and replace it with the requested terminal information architecture.
- [x] Command header, quote context, tabs, rail, main workspace, inspector and actual status probes.
- [x] Persistent workspaces, tab order/security, filters/configuration, import/export and reset.
- [x] Canonical registry, fuzzy commands, aliases, security context menu and honest unsupported routes.
- [x] Dense shared tables/charts, virtualized rows, first-column pinning, saved table views, CSV and report exports.
- [x] Rebuild Overview, Macro, Portfolio, Performance, Risk, Stress, Hedge and Backtest views.
- [x] Dynamic immutable stress jobs and configurable dataset-backed backtests.
- [x] Financial statements, DCF/comparables, SMA charts, watchlist and market inspection.
- [x] Validated CSV/JSON/XLSX import, catalogue/jobs, private notes and workbook/Pine workflows.
- [x] Add focused backend/unit/browser tests and four-size screenshot checks.
- [x] Pass the final fresh-database browser run: 10 tests and 33 existing screenshot comparisons, including mobile text containment.
- [ ] Complete specialist functions currently marked provider_required or in_development.
- [ ] Full panel docking, link groups, dataset/note/job command search and conflict-aware workspace syncing.
- [ ] Attribution, WACC builder, structured theses, factor IC/walk-forward and custom sandboxed strategy execution.
- [ ] Options repricing, real covariance stress, multi-asset hedge optimization, broker reconciliation and live data credentials.
- [ ] PDF/deck generation, arbitrary sheet previews, XLS/Parquet/Arrow/ZIP parsing and richer table exports.
- [ ] Production auth/CSRF/rate limits, encrypted TOTP secrets, per-user authorization and worker supervision.
- [ ] Full container startup and remote provider checks in a configured environment.

The older V1 checklist below is historical. Current capabilities and verification are in STATUS.md and docs/VISUAL_ACCEPTANCE.md.

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
