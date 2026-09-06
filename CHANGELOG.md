# CHANGELOG

## Terminal-only Scope Correction

- Pushed recovery tag pre-terminal-only-cleanup before removing visitor frontend source.
- Retained the private terminal and analytical engines as the sole product.
- Required authentication for investment pages and APIs, including demo and legacy aliases.
- Added noindex/no-store, opaque sessions, logout and private-route regression coverage.
- Removed the second frontend's workspace, Compose, environment and deployment configuration.

## Portfolio-First Operating Model - 2026-09-06

- Replaced market-first HOME with the KNK_MAIN Portfolio Command Centre while retaining the approved terminal shell.
- Added explicit SGD 70,000 opening contribution, 17 Decimal ledger kinds, native cash, immutable NAV/performance/risk records and provenance.
- Added trade review, risk contributions/limits, source comparison, stale-data retention, scoped demo reset and workbook reporting.
- Added durable file approval, 12 mapping profiles, immutable raw/curated versions, dataset-pinned research and imported financial statements.
- Added outbound OS-vault file agent and optional read-only paper snapshot reader with explicit fill-to-ledger approval.
- Added Equity/Quant/Risk & Trade desks, measured factor IC/quantiles and research-only candidate records; expanded registry to 110 functions.
- Added migration 0003, accounting/agent/broker tests and cross-viewport browser acceptance. Live services and production limitations remain explicit in STATUS.md.
- Restored Git tracking in C:\Dev without replacing transferred files; rebuilt copied dependency links outside OneDrive.
- Fixed compact-container seed startup, deterministic correlation ordering and source labels; verified API/PostgreSQL/Redis readiness and zero NAV reconciliation difference in Docker.

## Terminal UI V2 - 2026-09-06

- Rebuilt the terminal shell around compact command/security/tab bars, function navigation, persistent workspaces, analytical panels, resizable inspector and measured status.
- Added a canonical 102-function registry with explicit availability, provider and development states; replaced raw-JSON views with tables, charts and configured workflows.
- Added immutable stress runs, isolated backtesting.py jobs, validated CSV/JSON/XLSX imports, synthetic financials/DCF, private research editing and trusted-formula report exports.
- Reconstructed performance from the ledger and risk from aligned closes; validated manual transactions and retained broker read-only behavior.
- Added migration 0002, same-origin API/session proxy, import validation, source/timestamp labeling and cross-viewport browser regression coverage.
- Preserved the public site's design and retained explicit limits for unimplemented/provider-dependent functionality.

## 0.2.0 - 2026-09-05

- Replaced static demo API payloads with SQLAlchemy repositories, Alembic migration `0001_core_schema`, and deterministic database seeding.
- Added provider abstractions and a real FRED adapter with official API parameters, Pydantic parsing, retries, timeouts, raw JSON preservation, macro normalization, and mixed-source status handling.
- Added API-backed terminal pages for overview, macro, portfolio, positions, performance, risk, stress, hedge, strategies, backtests, factor lab, data drop, data catalogue, jobs, connections, security, system health, and Pine export.
- Added portfolio ledger recalculation, cash/NAV/position/P&L snapshots, performance metrics, risk metrics, stress results, hedge recommendations, persisted moving-average backtest, upload/dataset persistence, and `.xlsx` report generation.
- Added TypeScript API client package, E2E smoke test, backend coverage reporting, Docker health-check improvements, Redis worker job updates, and stronger no-execution security evidence.
- Docker Compose config validates; full Compose build/startup remains blocked locally until Docker Desktop Linux engine is running.

## 0.1.0 - 2026-09-05

- Initial KnK Capital Terminal monorepo.
- Added public website, private terminal, FastAPI API, workers, report engine, and read-only broker agent.
- Added demo data, environment badges, provider states, security guardrails, Docker Compose, CI, and documentation.
