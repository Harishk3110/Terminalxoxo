# Gap Audit

Date: 2026-09-05

Current commit at audit start: `de69cd7`

## Commands Executed

- `git status --short --branch`
- `git log --oneline -10`
- `rg --files -g '!node_modules' -g '!.next' -g '!dist' -g '!coverage' -g '!*.tsbuildinfo'`
- `rg -n "TODO|FIXME|placeholder|mock|fake|hardcoded|DEMO_TRACE|SECURITIES|POSITIONS|return \\{|not implemented|disabled|coming soon" -S`
- `rg -n "placeOrder|cancelOrder|reqGlobalCancel|transmitOrder|modifyOrder|submitOrder|executeTrade|autoRebalance|autoHedge|Buy button|Sell button|Submit order|Transmit order" -S`

## Findings

| Area | Required | Current State | Defect | Remediation | Status |
|------|----------|---------------|--------|-------------|--------|
| Git | Use current branch and remote | `main` tracks `origin/main` | Clean and usable | Continue on current branch | OPERATIONAL |
| Public web | Sanitized public site backed by public API/content | Next.js app exists | Mostly static content | Keep route separation, connect to `/api/v1/public/content` where needed | PARTIAL |
| Terminal web | Operational frontend-to-backend workflows | Next.js app exists | Major panels import static arrays from `@knk/domain` | Add maintained API client and load portfolio, macro, risk, jobs, providers, reports from backend | PARTIAL |
| API routing | Versioned `/api/v1` APIs with services/repositories | FastAPI app exists | Routes are unversioned and return fixed dictionaries | Introduce `/api/v1`, service/repository layers, typed responses | PARTIAL |
| Persistence | PostgreSQL with migrations | None | Restart erases API state | Add SQLAlchemy models, Alembic migration, seed pipeline | MISSING |
| Database models | Operational tables across auth, reference, macro, portfolio, risk, quant, research, ops | None | No persisted domain state | Add SQLAlchemy models and migration for required table groups | MISSING |
| Demo pipeline | Mock provider to raw object to validation to database to API | Demo arrays in source | Demo data bypasses ingestion path | Add deterministic seed and ingestion services that persist raw and curated data | DEMO-BACKED |
| Redis jobs | Redis-backed persisted background jobs | None | No durable job state or worker queue | Add job models, Redis queue adapter, worker polling | MISSING |
| Object storage | MinIO/S3 raw objects | None | Provider and upload raw payloads are not preserved | Add object-storage adapter and raw-object records | MISSING |
| FRED | Official API adapter, no hardcoded credential | None | Macro provider is absent | Add FRED provider with httpx, retries, parsing, and docs | MISSING |
| Macro dashboard | Database-backed macro series and observations | Static route shell | No series database or charts from API | Add macro tables, seed data, APIs, dashboard data endpoint | MISSING |
| Security master | Internal instrument master with provider mappings | Small static array | No immutable persisted master | Seed persisted instruments and mappings | MISSING |
| Portfolio ledger | Transactions, cash, positions, NAV, P&L | Static positions | No transaction processing | Add ledger service and calculation tests | MISSING |
| Performance | TWR, CAGR, volatility, drawdown, Sharpe | Static KPI | No calculated snapshots | Add performance service and tests | MISSING |
| Risk/stress/hedge | VaR, CVaR, stress, hedge sizing | Static numbers | No calculated risk engine | Add risk and hedge services with persisted outputs | MISSING |
| Backtesting | Strategy persistence and results | Static route shell | No strategy/backtest persistence | Add strategy and backtest services | MISSING |
| Data Drop | Upload, preview, map, import, catalogue | Static route shell | No file ingestion | Add upload APIs, storage, column inference, dataset records | MISSING |
| Reports | Actual XLSX outputs | Queue-like response only | No generated workbook | Add report generation and download API | MISSING |
| Pine export | Functional script generation | Static text | No compatibility report or export | Add Pine generator and tests | MISSING |
| Monitoring | Health/readiness/metrics from dependencies | Basic process health | Does not check database, Redis, storage, jobs | Add system health service and metrics | PARTIAL |
| Docker | Full stack starts and stays healthy | Compose exists | Missing minio-init, orchestrator, migrations, seeding, health detail | Update Compose, Dockerfiles, scripts | PARTIAL |
| Tests | Substantive financial and integration coverage | 4 API tests and 3 TS unit tests | Insufficient coverage | Add unit and integration tests for financial logic, providers, uploads, reports, isolation | PARTIAL |
| No execution | No broker execution capability | Security scan passes | Test scans docs too rigidly and implementation boundary is simple | Keep scan and route broker agent read-only | OPERATIONAL |

## Classification Summary

- OPERATIONAL: current git branch/remote, basic safety scan.
- DEMO-BACKED: current market/portfolio/risk demo values.
- PARTIAL: public web, terminal web, API, monitoring, Docker, tests.
- MISSING: persistence, migrations, Redis jobs, object storage, FRED, macro ingestion, real ledger, performance/risk engines, data drop, reports, Pine export.
- BROKEN: Docker validation when Docker Desktop Linux engine is stopped.

This audit is not an acceptance pass. It is the baseline for remediation.

## Post-Remediation Delta

Validated after implementation:

- Persistence, migrations, demo seed, API-backed terminal pages, FRED mocked provider, portfolio ledger, risk/hedge/performance calculations, upload/dataset flow, report generation, Pine export, security scan, frontend builds, and E2E smoke moved from missing/partial to operational or demo-backed.
- Docker Compose config moved to operational, but full Docker build/startup remains blocked by the local Docker Desktop Linux engine being stopped.
- Backend coverage is measured at 81% overall, but the directive's per-module coverage targets remain incomplete.
- Live FRED is implemented but pending a real `FRED_API_KEY`.
