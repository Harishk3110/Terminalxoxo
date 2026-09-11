# Build Evidence

## Final Master Build: 2026-09-11

Baseline `597f346b75033a7f1c322188751db3dc6b365a90`; remote
https://github.com/Harishk3110/Terminalxoxo.git. The following records supersede
archived claims below. Commands execute in C:\Dev unless stated otherwise.
Rows identify the checked-out commit; `+ worktree` means the changes being tested
were not committed yet. No full final-acceptance pass is claimed.

| Date | Commit | Command | Exit | Result |
| --- | --- | --- | --- | --- |
| 2026-09-11 | 597f346 | git status; git branch --show-current; git rev-parse HEAD; git log --oneline -15; git remote -v (separate invocations) | 0 each | PASS: clean main, expected remote. |
| 2026-09-11 | 597f346 | git tag -a pre-final-knk-terminal-build -m "Recovery baseline before final KnK terminal production build" | 0 | PASS |
| 2026-09-11 | 597f346 | git push origin pre-final-knk-terminal-build | 0 | PASS: new tag pushed. |
| 2026-09-11 | 597f346 + worktree | .venv-sprint/Scripts/python.exe -m pytest tests/sprint/test_final_loc_report.py tests/sprint/test_loc_counter.py -q | 0 | PASS: 71 tests, one dependency warning. |
| 2026-09-11 | 597f346 + worktree | .venv-sprint/Scripts/python.exe scripts/loc_report.py | 0 | PASS: 47,617 eligible lines; source 34,861, tests 12,756. Mixed sprint suites conservatively grouped as integration. |
| 2026-09-11 | 597f346 + worktree | corepack pnpm dlx node@22 node_modules/next/dist/bin/next build (apps/terminal-web; NEXT_PUBLIC_APP_ENV=test, KNK_API_URL=http://127.0.0.1:8000) | 0 | PASS: Next 15.5.24, private dynamic catchall/backend routes, login/static robots only. |
| 2026-09-11 | 597f346 | docker info --format '{{.ServerVersion}}' (initial) | 1 | FAIL: daemon pipe absent. |
| 2026-09-11 | 597f346 + worktree | docker info --format '{{.ServerVersion}}' (after hidden Docker Desktop startup) | 0 | PASS: daemon 29.4.2. This is not Compose health. |
| 2026-09-11 | 597f346 + worktree | docker ps -a --format '{{.Names}} {{.Status}} {{.Ports}}'; docker volume ls --format '{{.Name}}' (separate invocations) | 0 each | No containers; two unrelated anonymous volumes. Neither removed. |

## Security and Runtime Checkpoint

All rows below were run on `08b1233 + worktree`, 2026-09-11. Private databases,
credentials, screenshots and machine-readable results remain ignored local
artifacts, not committed account data. The code changes are the next checkpoint.

| Command / Check | Exit | Result |
| --- | --- | --- |
| pytest tests/sprint/test_auth_enrollment.py -q | 0 | 20 passed. Encrypted/expired enrollment, replay, recovery reuse, password and session ownership. |
| Focused auth + telemetry pytest with coverage | 0 | 22 passed; 252/269 lines, 93.68%. `logs/final-auth-coverage.json`. |
| mypy auth_models.py auth_security.py auth_api.py auth_guards.py --follow-imports=silent | 0 | Four changed modules pass strict typing. `logs/final-auth-types.log`. |
| Ruff changed security/telemetry/bootstrap/migration and focused tests | 0 | Passed. Does not certify all application files. |
| pytest tests/sprint services/api/tests --cov=app (first) | 1 | 914 passed, eight failed. Invalid metrics fixture, obsolete migration-head assertion and date-sensitive integration assumptions. The broad import name also double-counted alias-loaded files; this coverage denominator is not used. |
| Same suites --cov=services/api/app (second) | 1 | 918 passed, five failed: a completely frozen fixture reused unique NAV timestamps. `logs/final-backend-regression-r2.log`. |
| Same suites --cov=services/api/app --cov-report=json:logs/final-backend-coverage-r3.json (third) | 0 | 923 passed, 13 warnings, 277.31s. Snapshot tests pin the day but retain advancing time; a separate test confirms old demo marks remain STALE. |
| corepack pnpm test-unit | 0 | 235 terminal + three domain + two function-registry tests passed. `logs/final-frontend-unit.log`. |
| corepack pnpm lint | 0 | Workspace frontend lint passed. Host Node 20 engine warning retained; production build uses Node 22. |
| corepack pnpm typecheck (initial/retry) | 2 / 0 | Removed unsupported test-only Testing Library `exact` role option; all workspace TypeScript checks then passed. `logs/final-frontend-types-r2.log`. |
| corepack pnpm security-check | 0 | No forbidden broker action method names found. Not a full security audit. |
| python -m ruff check services/api/app | 1 | 218 errors. `logs/final-backend-lint.log`. |
| python -m mypy services/api/app | 1 | 1,260 errors / 56 files, 102 source files checked. `logs/final-backend-types.log`. |
| SQLite Alembic upgrade head; downgrade base; upgrade head (separate commands) | 0 each | Six revisions in isolated `logs/final-migrations-01.db`; no user database reset. |
| scripts/prepare_local_stack.py; Compose config --quiet | 0 each | New ignored `.env.compose.local`, random credentials, existing `.env` retained. Repeated bootstrap preserves the existing file. |
| docker compose --env-file .env.compose.local --progress plain build terminal-web api worker-data worker-quant | 0 | Node 22 / Next 15.5.24 production image and Python images built. `logs/final-docker-production-build.log`. |
| Compose up -d and ps | 0 | API, terminal, PostgreSQL, Redis, MinIO, both queue workers, Prometheus and Grafana healthy. Report-engine omitted because its readiness intentionally fails. |
| PostgreSQL isolated Alembic roundtrip | 0 | upgrade head -> downgrade base -> upgrade head in newly created `knk_migration_verify_20260911`; head `0006_auth_totp_state`. `logs/final-postgres-migrations.log`. Active `knk_terminal` was not dropped or reset. |
| PostgreSQL KNK_MAIN query | 0 | `KnK Capital Main Portfolio`, reference capital `100000.00000000`, code `KNK_MAIN`. |
| Playwright security/privacy first run | 1 | Two privacy tests passed; auth test exposed inherited cookies in its second browser context. Result retained in `logs/final-security-01-results.json`. |
| Playwright security/privacy second run | 0 | Three passed, 44.0s; explicit empty second-context storage state. `logs/final-security-02-results.json`. |
| corepack pnpm test-e2e, PLAYWRIGHT_RUN_ID=final-full-01 | 1 | 28 passed, seven failed, 7.1 minutes. `logs/final-browser-full-results.json`. Not a final visual/functional pass. |
| Playwright multi-security backtest targeted retry | 0 | One passed, 54.0s, after explicit start date and polling the submitted run ID instead of an older success badge. `logs/final-browser-backtest-r2-results.json`. |
| Local production setup page, browser + HTTP probes | 0 | /overview -> /login 200; noindex; CSS 200/45,884 bytes/476 rules; no browser errors or horizontal overflow at 1440 and 390. `logs/live-login-1440.png`, `logs/live-login-390.png`. No live administrator created. |
| Prometheus target + authenticated Grafana catalogue | 0 | `knk-api` target up, no scrape error; dashboard UID `knk-platform`, title `KnK Platform Overview`. One dashboard, not all nine. |
| scripts/loc_report.py | 0 | 48,915 meaningful lines: 35,642 source, 13,273 tests. Generated assets, dependencies, databases, docs and comments excluded. |

### Coverage Scope

Measured from the passing third backend invocation. These are weighted statement/
line totals, not averages of file percentages, branch coverage or proof that every
requested feature exists. Twenty-five lines excluded by the existing coverage
configuration; all 10,891 counted application statements remain in the denominator.

| Package / Selection | Covered / Statements | Coverage |
| --- | --- | --- |
| Entire API application | 9,429 / 10,891 | 86.58% |
| portfolio_domain | 1,000 / 1,018 | 98.23% |
| portfolio_valuation | 362 / 371 | 97.57% |
| performance_domain | 341 / 367 | 92.92% |
| risk_statistics | 85 / 87 | 97.70% |
| option_greeks + options_analytics | 224 / 241 | 92.95% |
| auth_api + auth_security + auth_guards | 244 / 256 | 95.31% |
| backtest_engine | 178 / 194 | 91.75% |
| alpha_statistics | 55 / 61 | 90.16% |
| equity_valuation | 130 / 134 | 97.01% |
| data_drop | 163 / 183 | 89.07% |
| queue_worker | 47 / 82 | 57.32% |

Remaining browser failures are hedge calculation, stress calculation and four
dependent desktop visual workflows. Stress rejects missing beta history rather
than fabricating a result; the seeded observations end on September 4. A proper
dated/source-pinned analytical workflow and independent success/error-state visual
fixtures are still needed. Do not update screenshots or weaken guards to conceal
this. The corrected backtest has only a targeted rerun, not a new full-suite pass.

Managed PostgreSQL/object backup-restore, all reports, trusted devices, broader
security review, all-service Compose health and the full 197-step final acceptance
remain incomplete. No public production deployment is claimed.

## Archived V1 Evidence

This is the archived V1 evidence. Current terminal V2 results are in STATUS.md and docs/VISUAL_ACCEPTANCE.md.

Date: 2026-09-05

Base commit at validation start: `de69cd7`

Remote: `https://github.com/Harishk3110/Terminalxoxo.git`

## Evidence Table

| Gate | Command | Exit | Summary |
|------|---------|------|---------|
| Git status | `git status --short --branch` | 0 | `## main...origin/main`; worktree dirty with remediation changes before commit. |
| Python dependency sync | `python -m pip install -r services/api/requirements.txt` | 0 | Installed/satisfied FastAPI, SQLAlchemy, Alembic, psycopg, Redis, boto3, pytest-cov, XlsxWriter, FRED HTTP deps. |
| Worker/report dependency sync | `python -m pip install -r services/worker-quant/requirements.txt`; `python -m pip install -r services/report-engine/requirements.txt` | 0 | Installed/satisfied NumPy/SciPy/SQLAlchemy/psycopg and report engine XLSX/PPTX dependencies. |
| JavaScript dependency sync | `corepack pnpm install` | 0 | Workspace dependencies resolved after adding `packages/api-client`. |
| Alembic migration | `$env:DATABASE_URL='sqlite:///./knk_terminal_validation_20260905.db'; python -m alembic upgrade head; python -m alembic downgrade base; python -m alembic upgrade head` | 0 | SQLite clean upgrade/downgrade/upgrade passed for revision `0001_core_schema`. |
| Demo seed | `$env:DATABASE_URL='sqlite:///./knk_terminal_validation_20260905.db'; python services/api/scripts/seed_demo.py --reset` | 0 | Seeded counts: alerts 2, backtests 1, data_quality_issues 1, datasets 2, factor_runs 1, instruments 20, jobs 2, macro_observations 2040, macro_series 17, research_notes 2, system_health_snapshots 8, transactions 7. |
| Backend compile | `python -m compileall -q services/api/app services/api/scripts services/worker-data/app services/worker-quant/app services/report-engine/app services/broker-agent` | 0 | Python syntax/import compile check passed. |
| Backend tests | `$env:DATABASE_URL='sqlite:///./knk_terminal_validation_tests_final.db'; python -m pytest services/api/tests` | 0 | `15 passed, 3 warnings in 46.92s`. |
| Backend coverage | `$env:DATABASE_URL='sqlite:///./knk_terminal_coverage_20260905.db'; python -m pytest services/api/tests --cov=services/api/app --cov-report=term-missing` | 0 | `15 passed`; total backend app coverage 81%. |
| Backend lint | Not run | N/A | No Ruff/mypy backend lint/typecheck gate is configured yet. |
| Frontend typecheck | `corepack pnpm typecheck` | 0 | All workspace TypeScript typechecks passed. |
| Frontend lint | `corepack pnpm lint` | 0 | All package TS checks passed; Next lint for public and terminal had no warnings/errors. |
| Frontend tests/security | `corepack pnpm test` | 0 | 3 Vitest domain tests passed; security guard reported no forbidden broker action method names in application source. Some packages still have echo-only test scripts. |
| Terminal production build | `corepack pnpm --filter @knk/terminal-web build` | 0 | Next build passed; `/[[...slug]]` dynamic route and `/_not-found` generated. |
| Docker Compose config | `docker compose config --quiet` | 0 | Compose YAML validates. |
| Docker Compose build | `docker compose build` | 1 | Failed before build because Docker Desktop Linux engine was unavailable at `npipe:////./pipe/dockerDesktopLinuxEngine`. |
| Docker Compose startup | `docker compose up --build` | Not run | Not run because Docker engine is unavailable; cannot truthfully mark service health passed. |
| E2E tests | `$env:PLAYWRIGHT_RUN_ID='manual-20260905h'; corepack pnpm test-e2e` | 0 | Chromium installed; `1 passed` validating API-backed terminal Overview, Macro, and Connections. |
| Security scan | `corepack pnpm security-check` | 0 | No forbidden broker execution method names found in application source. |
| Secret scan | `rg -n -I "AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|FRED_API_KEY=[a-z0-9]{32}" ...` | 0 | No matches. |
| Explicit no-execution search | `rg -n "placeOrder|cancelOrder|reqGlobalCancel|transmitOrder|modifyOrder|submitOrder|executeTrade|autoRebalance|autoHedge|Buy button|Sell button|Submit order|Transmit order|Cancel broker order|Live execution toggle" ...` | 0 | Only `docs/GAP_AUDIT.md` contains the command reference; application source is clean. |
| Acceptance script | `scripts/acceptance.ps1` | Not run | Equivalent commands were run individually; full script not run because Docker engine is unavailable. |
| Source line count | `rg --files ... | Measure-Object` | 0 | `files=172 lines=6696`, excluding node_modules, Next outputs, dist/build/coverage, lock files, DBs, and generated outputs. |

## Docker Blocker

Docker CLI version output:

```text
Client:
 Version:           29.4.2
 Context:           desktop-linux
failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine; check if the path is correct and if the daemon is running: open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

Action required: start Docker Desktop and enable the Linux engine, then rerun `docker compose build`, `docker compose up --build`, and `scripts/wait-for-services.ps1`.
