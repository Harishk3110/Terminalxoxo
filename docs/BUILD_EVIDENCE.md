# Build Evidence

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
| Public production build | `corepack pnpm --filter @knk/public-web build` | 0 | Next build passed; `/[[...slug]]` dynamic route and `/_not-found` generated. |
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
