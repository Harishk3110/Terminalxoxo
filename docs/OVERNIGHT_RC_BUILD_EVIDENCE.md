# Overnight Build Evidence

Baseline: 3466694, main, 2026-09-12 SGT. These observations are not a release pass.

| Command | Result | Evidence |
| --- | --- | --- |
| git status --short; branch; rev-parse; log -15; remote -v; diff --check (separate calls) | all exit 0 | Clean expected main and remote |
| git tag -a pre-overnight-rc-closure; git push origin pre-overnight-rc-closure | exit 0 each | Recovery tag pushed |
| docker compose --env-file .env.compose.local ps --all | exit 0 | Nine long-running services healthy, init exit 0; report absent |
| python -m ruff check services/api/app | failed | logs/overnight-baseline-ruff.log: 218 errors; shell tail exit was 0, NOT Ruff success |
| python -m mypy services/api/app | failed | logs/overnight-baseline-mypy.log: 1,260 errors / 56 files; tail exit not mypy success |
| python -m pytest tests/sprint services/api/tests --collect-only -q | exit 0 | 923 collected, 26.70 seconds; no execution claim |

Runtime data and credentials have not been reset. Pending code is unverified
until concrete tests are recorded here.

## M1 Pipeline, 2026-09-12 00:24-00:42 SGT

All commands use 3466694 + worktree, not final release code.

| Command / check | Exit | Evidence |
| --- | --- | --- |
| pytest report jobs | 0 | 29 initially, then 30 after lease-race fix, then 34 with health/S3/native chart checks |
| pytest reports + legacy contracts + migrations | 0 | 46 passed; later expanded migration ownership selection 48 passed |
| mypy seven report modules --follow-imports=silent | 0 after fixes | Initial 21 then 6 errors corrected; one narrow XlsxWriter missing-stub import ignore, no module exclusion |
| mypy reports + watchdog --follow-imports=silent | 0 | Eight modules; subsequent native-chart inference fix also passed |
| pnpm typecheck / lint | 0 each | New report UI included; later typecheck also passed |
| pnpm test-unit | 0 | 235 terminal + 5 shared initially; three added report-control tests passed |
| Node 22 next build without environment | 1 | Fail-closed API-origin validation, corrected to explicit local test environment |
| Node 22 next build with local test environment | 0 | No private static pages; rebuilt after responsive fix |
| Docker API/reports/data/quant/frontend images | 0 | Production builds; non-root Node frontend |
| Full pytest, KNK_ENV=test, isolated DB | 1 | logs/overnight-backend-01.log: 949 passed / 3 failed; secure cookies/local-key restrictions incompatible with local HTTP test assumptions |
| Auth selection with KNK_ENV=local-demo | 0 | 47 passed, security behavior unchanged |
| Full pytest, KNK_ENV=local-demo, isolated DB | 0 | logs/overnight-backend-02.log: 959 passed / 13 warnings / 294.49s; 9,856/11,385 lines = 86.5700%, 25 existing excluded; not branch coverage |
| Playwright reports initial | 0 | logs/overnight-reports-browser-01.log: 1 passed, 18.5s; visual review caught resize overlay |
| Playwright reports after resize/persistence fix | 0 | logs/overnight-reports-browser-02.log: 1 passed, 22.1s; inspected 1440px/390px screenshots |
| PostgreSQL report smoke initial | 1 | Incorrect expected setup status 201; endpoint actually returns 200 |
| PostgreSQL report smoke corrected | 0 | logs/overnight-report-postgres-smoke-02.log; new DB knk_report_verify_20260911_163424_2b35e2; XLSX 44,059 / PPTX 172,413 / PDF 65,537 bytes; hashes verified, anonymous 401, files retained after worker stop |
| PostgreSQL fresh head / latest down / head | 0 | New DB knk_report_migration_e07f1e22ffc8, seven migrations, report_jobs present |
| pytest watchdog | 0 | Three tests, bounded restarts and no data-reset commands |
| watchdog --once --observe-only | 1 then 0 | First observed Prometheus immediately after intentional restart; later all ten services healthy, init succeeded |
| secret scan / broker-action scan / diff check | 0 each | 526 text files, zero secrets; no broker action methods |

No active database was restored over. Private logs retain hashes and failure
evidence. The full 959-test run preceded the final native-chart test addition;
its 34-test report follow-up passed. Full report-model content, artifact rendering,
global types and the full browser suite are not certified by this checkpoint.
