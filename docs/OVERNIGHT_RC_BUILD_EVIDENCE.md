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

## M2 Static Cleanup, First Batch

Based on c1abce4 + worktree. Ruff safe fixes and formatting covered first-party
services, scripts, infrastructure, migrations and tests. Named FastAPI dependency
defaults preserve direct positional callers and route registration order.

| Check | Result |
| --- | --- |
| Ruff baseline, all first-party Python | 276 findings before fixes |
| Ruff / format after fixes, including five local stubs | Exit 0 / exit 0; 230 files formatted |
| Targeted report/auth/migration regression | 69 passed, 3 warnings, 41.40s |
| Provider baseline contracts | 18 passed, 3 warnings, 6.13s |
| New transport non-finite regressions, first attempt | 3 failed / 78 passed; Pydantic JsonValue accepts non-finite floats despite configuration |
| Corrected explicit JSON constant/exponent rejection | 82 passed; logs/overnight-boundaries-tests-03.log |
| Strict mypy on 11 boundary modules | Exit 0; logs/overnight-mypy-boundaries-03.log |
| Runtime stubtest for used vollib signatures | Exit 0, 7 modules; no missing-stub requirement for unused third-party API |
| Full API mypy | Still fails: 1,140 errors in 46 files; logs/overnight-mypy-m2b.log |
| OpenAPI generation | Exit 0; 170 paths, 69 schemas; report body resolves to ReportRequest |
| Execution-method scan / diff check | Exit 0 each |
| Secret scan after formatting | One dummy FRED fixture key flagged; replaced with explicit mock-fred-key, scanner unchanged |

The original full mypy baseline was 1,260 errors / 56 files. No first-party module
was excluded or globally silenced. Added development-only boto3 S3 stubs pinned to
the existing boto3 version, and five narrow vollib signature files checked against
the installed library. Provider JSON and SEC filing columns now reject malformed
values explicitly. The first M2 full run (overnight-backend-03.log) ended with
959 passes and 14 fixture-setup errors: Ruff removed imports used by pytest's
fixture discovery. Explicit fixture re-exports restored that registration without
disabling any lint rule. The affected selection then passed all 17 tests in 39.33s.
The corrected full rerun passed: 973 tests, zero failures, 13 warnings, 265.59s,
in overnight-backend-04.log. Coverage: 9,950/11,456 statements, 1,506 missing,
23 existing exclusions; statement coverage, not branch coverage (86.85405027932961%).
The four API/data/quant/report Docker images rebuilt successfully using the
production dependency set (overnight-m2-docker-build.log).
The post-fixture-fix Ruff and format checks passed. The secret scanner examined
531 eligible text files with zero findings; the existing scanner was unchanged.

Bounded watchdog started hidden with launcher PID 10020; persistent JSONL receipts
show all ten daemons healthy and successful MinIO init. Runtime images still carry
the preceding report checkpoint while this source batch is verified.

## M2 Model And Source Contracts, Second Batch

Based on 0769543 + worktree. SQL Date annotations now match their existing SQL
types; persisted JSON and repository write contracts are explicit. No schema or
data migration was introduced. Historical inverse FX is bounded by the requested
date, malformed dataset schemas fail before writes, and absent volume stays null.

| Check | Result |
| --- | --- |
| First M2 runtime refresh | Exit 0; overnight-m2-docker-up.log; ten daemons healthy |
| Strict mypy on model/repository/price-source contracts | Exit 0; five modules |
| Date invariant, first attempt | Failed: adjacent Date columns escaped mechanical replacement; fixed every Date field |
| Contract/migration regression | 27 passed, 15.54s; overnight-model-contracts-tests-03.log |
| Provider/repository/portfolio selection | 58 passed, 7.89s; overnight-source-contracts-tests.log |
| Full API mypy | Still fails: 1,248 errors / 44 files; overnight-mypy-m2c.log |
| Full backend with isolated SQLite/objects | 985 passed, 13 warnings, 298.52s; overnight-backend-05.log |
| Statement coverage | 10,126/11,625 = 87.10537634408603%; 1,499 missing, 23 existing exclusions; no branch claim |
| Frontend typecheck / lint | Exit 0 each; overnight-m2c-typecheck.log / overnight-m2c-frontend-lint.log |
| Frontend units | 240 terminal + 5 shared passed; overnight-frontend-unit-03.log |
| Report browser workflow, no retries | 1 passed, 17.4s; overnight-m2c-reports-browser.log |
| Report screenshots | reports-1440.png and reports-390.png inspected; mobile inspector hidden without overlap |
| Four production backend images | Exit 0; overnight-m2c-docker-build.log; refresh pending |
| Whole first-party Ruff / format | Exit 0 each; 239 Python/stub files formatted |

The browser harness now detects any TCP listener on all three isolated service
ports, including HTTP error responses, without terminating foreign listeners.
Two focused tests cover this guard. Stronger persisted model types expose more
unchecked callers; the global mypy gate remains open, not silently excluded.
