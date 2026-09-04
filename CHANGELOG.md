# CHANGELOG

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
