# Core Acceptance Evidence

This is the archived V1 evidence from 2026-09-05. Current terminal V2 results are in STATUS.md and docs/VISUAL_ACCEPTANCE.md.

Acceptance entries are marked PASS only after the listed command exits 0.

| Requirement | Verification Command | Expected Result | Actual Result | Status | Evidence Reference |
|-------------|----------------------|-----------------|---------------|--------|--------------------|
| Current branch and remote preserved | `git status --short --branch`; `git remote -v` | `main` tracking `origin` Terminalxoxo | `## main...origin/main`; `origin https://github.com/Harishk3110/Terminalxoxo.git` | PASS | `STATUS.md` |
| Gap audit created | Review `docs/GAP_AUDIT.md` | Audit table with required/current/defect/remediation/status | File created before remediation | PASS | `docs/GAP_AUDIT.md` |
| Alembic clean migration cycle | `$env:DATABASE_URL='sqlite:///./knk_terminal_validation_20260905.db'; python -m alembic upgrade head; python -m alembic downgrade base; python -m alembic upgrade head` | Exit 0 | Exit 0; revision `0001_core_schema` upgraded, downgraded, upgraded | PASS | `docs/BUILD_EVIDENCE.md` |
| Deterministic demo seed persists records | `$env:DATABASE_URL='sqlite:///./knk_terminal_validation_20260905.db'; python services/api/scripts/seed_demo.py --reset` | Exit 0 and seeded operational rows | Exit 0; 20 instruments, 2040 macro observations, 7 transactions, 2 jobs, 2 datasets, 1 factor run | PASS | `docs/BUILD_EVIDENCE.md` |
| Backend syntax compiles | `python -m compileall -q services/api/app services/api/scripts services/worker-data/app services/worker-quant/app services/report-engine/app services/broker-agent` | Exit 0 | Exit 0 | PASS | `docs/BUILD_EVIDENCE.md` |
| Backend tests pass | `$env:DATABASE_URL='sqlite:///./knk_terminal_validation_tests.db'; python -m pytest services/api/tests` | Exit 0 | `15 passed, 3 warnings` | PASS | `docs/BUILD_EVIDENCE.md` |
| Backend coverage measured | `$env:DATABASE_URL='sqlite:///./knk_terminal_coverage_20260905.db'; python -m pytest services/api/tests --cov=services/api/app --cov-report=term-missing` | Exact percentage reported | `15 passed`; total coverage 81% | PASS | `docs/BUILD_EVIDENCE.md` |
| FRED mocked provider parses observations and vintages | `python -m pytest services/api/tests/test_fred_provider.py` | Exit 0 | Included in backend suite; passed | PASS | `services/api/tests/test_fred_provider.py` |
| Public/private API separation tested | `python -m pytest services/api/tests/test_api.py` | Public endpoint excludes private records/secrets | Included in backend suite; passed | PASS | `services/api/tests/test_api.py` |
| Forbidden broker execution strings absent from app source | `corepack pnpm security-check` | Exit 0 | Exit 0; no forbidden method names found in application source | PASS | `tests/security/no-execution-methods.mjs` |
| Explicit forbidden string search performed | `rg -n "placeOrder|cancelOrder|reqGlobalCancel|transmitOrder|modifyOrder|submitOrder|executeTrade|autoRebalance|autoHedge|Buy button|Sell button|Submit order|Transmit order|Cancel broker order|Live execution toggle" ...` | No application source matches | Only `docs/GAP_AUDIT.md` command reference matched | PASS | `docs/BUILD_EVIDENCE.md` |
| Frontend typecheck | `corepack pnpm typecheck` | Exit 0 | Exit 0 | PASS | `docs/BUILD_EVIDENCE.md` |
| Frontend lint | `corepack pnpm lint` | Exit 0 | Exit 0 | PASS | `docs/BUILD_EVIDENCE.md` |
| Workspace tests | `corepack pnpm test` | Exit 0 | Exit 0; 3 Vitest tests passed, security scan passed; some packages still echo-only | PASS | `docs/BUILD_EVIDENCE.md` |
| Frontend production build | `corepack pnpm --filter @knk/public-web build`; `corepack pnpm --filter @knk/terminal-web build` | Exit 0 for both apps | Exit 0 for both; route reports generated | PASS | `docs/BUILD_EVIDENCE.md` |
| E2E terminal journey | `PLAYWRIGHT_RUN_ID=manual-20260905h corepack pnpm test-e2e` | Exit 0 | `1 passed`; Chromium installed and UI/API smoke passed | PASS | `tests/e2e/smoke.spec.ts` |
| Docker Compose config | `docker compose config --quiet` | Exit 0 | Exit 0 | PASS | `docs/BUILD_EVIDENCE.md` |
| Docker Compose build | `docker compose build` | Exit 0 | Exit 1; Docker Desktop Linux engine not reachable | FAIL | `docs/BUILD_EVIDENCE.md` |
| Docker Compose startup/health | `docker compose up --build` and `scripts/wait-for-services.ps1` | Healthy services | Not executed because Docker engine is unavailable | FAIL | `STATUS.md` |
| Live FRED smoke | External live test with `FRED_ENABLED=true` and `FRED_API_KEY` | Connected provider and persisted FRED rows | Not executed; no credentials configured | PENDING | `docs/FRED_PROVIDER.md` |
| Backend lint | Ruff/mypy or equivalent | Exit 0 | Not configured | PENDING | `TASKS.md` |
| Source line count | PowerShell `rg --files ...` count command | Non-generated count reported | `files=172 lines=6696` | PASS | `docs/BUILD_EVIDENCE.md` |
