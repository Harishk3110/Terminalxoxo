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

## M2 Consumers And Watchdog Recovery, Third Batch

Based on 63a9db4 + worktree. Provider responses, durable queue dispatch, seed
lookups and hash-verified research JSON now have explicit contracts. No financial
formula, demo observation date, authentication gate or execution policy was relaxed.

| Check | Result |
| --- | --- |
| Second M2 runtime refresh, first attempt | Exit 1; API exited 137 after watchdog interrupted normal startup, not an OOM |
| Watchdog diagnosis | Receipts recorded API restart during health=starting and Prometheus restart for a down report target |
| Watchdog correction | Starting stays STARTING without restart; healthy Prometheus reports upstream failure without restart; API live and ready both checked |
| Watchdog unit / recovery | Six passed; recover Compose exit 0, all ten services observed healthy; old owned processes stopped and corrected hidden launcher PID 24200 started |
| Strict mypy, eight consumers/watchdog | Exit 0; overnight-mypy-consumers-05.log |
| Full API mypy | Still fails: 1,119 errors / 37 files; overnight-mypy-m2d.log |
| Focused regression, first attempt | 1 failed / 54 passed; PriceObservation revalidation rejected the adapter's derived date alias |
| Alias handling corrected, expanded regression | 96 passed, 10.87s; overnight-consumers-tests-02.log |
| Full backend, isolated SQLite/objects | 1,029 passed, 13 warnings, 336.48s; overnight-backend-06.log |
| Statement coverage | 10,267/11,752 = 87.36385296119809%; 1,485 missing, 23 existing exclusions |
| OpenAPI generation | Exit 0; 170 paths, 73 schemas, typed provider response schemas included |
| Four production backend images | Exit 0; overnight-m2d-docker-build.log; refresh pending |
| Whole Ruff / format | Exit 0 each; scope includes infrastructure and migrations, 254 files before template tests |
| Execution-method / secret scans | Exit 0 each; 536 eligible text files, zero secret findings before templates |
| Full Playwright, no retries | In progress in overnight-browser-full-01.log; hedge failure reproduced; no full-pass claim |

The exact-one-observation guard prevents a response-less provider success record.
Non-finite values and malformed metadata are rejected even when a dataset hash
matches. SEC nested facts cannot overwrite their enclosing taxonomy/concept/unit.
Queue actor types fail before network access. Missing portfolio parents fail before
archive or seed mutations. Additional tests cover these boundaries.

## Fictional Onboarding Templates

Seven CSV files and field definitions were added under templates. They use a
fictional SAMPLE_EQ security and fixed historical dates, not user financial data.
The first normalization run had six passes and one failure because the options
profile expects an underlying column. The template header was corrected to that
existing alias; all seven parser/profile tests passed on the second run, recorded
in overnight-import-templates-tests-02.log. These seven tests were added after
the full 1,029-test run started and are separately verified, not included in it.
No template was imported into KNK_MAIN or the active local database.
Post-template whole Ruff/format and secret scans passed: 255 formatted Python/stub
files and 545 eligible text files with zero secret findings. Diff check also passed.

## Dated Valuation And Broader Gate Diagnostics

Based on df8dab6 plus worktree. Historical valuation used to replace current
positions/cash/NAV projections. The regression failed before correction; historical
runs now keep their own immutable records and only today's run materializes the
current view. Version knk-nav-4.9 invalidates the prior cache. Stress and hedge
accept an explicit date or saved valuation, reject future/conflicting selections,
and retain the original observation timestamps and beta sufficiency requirements.

| Check | Result |
| --- | --- |
| Dated valuation focused regression | 28 passed; overnight-dated-valuation-tests-02.log |
| Full backend first attempt | 1,044 passed, four old-version assertion failures; overnight-backend-07.log |
| Full backend after exact expected-version update | 1,048 passed, 13 warnings, 340.00s; overnight-backend-08.log |
| Statement coverage | 10,313/11,784 = 87.51697216564834%; 1,471 missing, 23 existing exclusions |
| Frontend units | 240 terminal + 5 shared passed; overnight-dated-frontend-tests.log |
| TypeScript / lint / Node 22 build | Exit 0; overnight-dated-typecheck-02.log, overnight-dated-frontend-lint.log, overnight-dated-frontend-build.log |
| Five Docker image builds | Exit 0; overnight-dated-docker-build.log; runtime refresh pending |
| Original full browser | 30 passed, six failures; overnight-browser-full-01.log |
| Dated targeted browser second attempt | Six passed, 3.1m; overnight-dated-browser-02.log |
| Expanded 37-test full browser | In progress; three old-version expectations found, no full-pass claim |
| Whole Ruff / format | Exit 0 each; format reports 259 files; overnight-dated-ruff.log / overnight-dated-format.log |
| Distribution-aware strict runner | Completes nine distributions/237 inventoried files; 2,003 distinct diagnostic lines in 135 files, still FAIL |
| Runner unit tests / strict mypy | Eight passed; overnight-type-gate-tests-02.log; mypy exit 0 in overnight-type-gate-mypy-03.log |

The first flat whole-repository mypy command and its explicit-package-bases variant
both stopped on duplicate independent service modules. The new runner separates
deployment namespaces, covers every Git-visible first-party Python/stub file and
does not treat an inventory-only run as a pass. Its first grouped attempt exposed
two remaining tools/test namespace collisions; explicit bases in those groups
resolved them. Imported diagnostic repetitions were de-duplicated by complete
diagnostic line for the whole-run count, not summed across distributions.
The later runner test module is separately verified and not included in that
237-file inventory or the 1,048-test full backend run.

## Legacy Surface And Uploaded Backtest Closure

The unused inbound broker bridge no longer returns fake pairing, heartbeat or
account balances. It reports DISABLED, fails readiness, and refuses pairing and
snapshots. The actual outbound paper reader is unchanged. Retired report handler
annotations preserve the existing disabled behavior. The first three tests failed
during FastAPI registration because NoReturn is not a response-model type; normal
None-returning handlers that raise HTTPException fixed registration. The combined
retired-service and type-runner selection then passed all 11 tests.

The full backend rerun includes these additions: 1,059 passed, 13 warnings,
337.36s in overnight-backend-09.log. Statement coverage is 10,309/11,784 =
87.48302783435166%, with 1,475 missing and 23 existing exclusions. The latest
whole type run covers 239 files across nine groups and fails with 1,995 distinct
diagnostic lines in 133 files. Both retired modules and their tests pass scoped
strict mypy; no type ignores were introduced.

The second full browser run finished 34/37 with only old-version expectations.
The third finished 36/37, including populated alpha/GEX/hedge at every requested
size. Changing the uploaded CSV fixture from benchmark SPY to non-held QQQ exposed
two issues: the launch ignored normalized security context, and the test observed
an older successful run when submission failed. The UI now carries the validated
preview symbol, leaves unresolved dataset launches unselected, and does not load
an unrelated prior result into a new dataset tab. The test requires the actual
202 response and polls that exact ID in native USD without synthetic FX fallback.

| Check | Result |
| --- | --- |
| Backtest source unit tests | 11 passed, included in 251 terminal + 5 shared full unit tests |
| Frontend types / lint | Exit 0; overnight-backtest-handoff-typecheck.log / overnight-backtest-handoff-lint.log |
| Node 22 production build | Exit 0; overnight-backtest-handoff-build.log |
| Exact uploaded-run browser workflow | One passed, 1.2m; overnight-backtest-handoff-browser.log |
| Full browser with handoff correction | Running in overnight-browser-full-04.log; no full-pass claim yet |
| Docker frontend build | Running in overnight-backtest-handoff-docker-build.log |
| Whole Ruff / format | Exit 0; overnight-handoff-ruff.log / overnight-handoff-format.log |

The current screenshot matrix covers 19 routes (16 required workspaces plus
separate options/GEX, macro and risk), at five sizes. Direct review has confirmed
populated alpha/GEX on desktop and the overview, portfolio, performance, alpha,
equity, quant, GEX, risk/trade and hedge mobile layouts. Remaining screenshot
review and the complete release gates stay open.

## Saved Forms, Test Contracts And Managed Backup

2026-09-12 SGT, working tree based on ce3def3; branch main. Full browser run 04
completed with 37 passes, zero retries, 8.4m. The form-defaults batch preserves
explicit saved values while filling fields absent from older saved configurations.
Missing catalogue licence information is now labelled "Not recorded", not "Seed fixture".
44 Python test files gained explicit fixture/return contracts on 152 test functions.
The AST comparison confirms unchanged executable bodies and imported bindings.

| Command / check | Exit / result | Evidence under logs/ |
| --- | --- | --- |
| Full pytest rerun 10 | 0; 1,059 passed, 13 warnings, 340.58s | overnight-backend-10.log |
| Executable AST comparison | 0; 44 files preserve behavior/import bindings | overnight-test-types-ast.json |
| Frontend workspace units | 0; 254 terminal + 5 shared = 259 | overnight-form-defaults-tests.log |
| TypeScript / frontend lint | 0 / 0 | overnight-form-defaults-typecheck.log / overnight-form-defaults-lint.log |
| Node 22 production build | 0 | overnight-form-defaults-build.log |
| Frontend Docker build | 0 | overnight-form-defaults-docker-build.log |
| Whole strict types, run 05 | 1; 1,897 distinct diagnostic lines / 126 files / 245 sources / nine groups | python-types-05/manifest.json |
| Expanded full browser run 05 | 1; 33 passed / four duplicate-draft visual failures, 9.4m | overnight-browser-full-05.log |
| Corrected draft visuals 1440px/390px | 0; two passed, 1.8m | overnight-visual-drafts-target.log |
| Full browser run 06 | 0; 37 passed, zero retries, 8.9m | overnight-browser-full-06.log |
| Backup/health/legacy archive tests | 0; 50 passed before final probe/publication refinements | overnight-backup-health-tests-02.log |
| Real PostgreSQL/S3 integration 03 | 0; one passed, 6.55s, 31 upstream deprecation warnings | overnight-managed-backup-integration-03.log |
| promtool configuration/rules check | 0 | overnight-backup-alerts-validation.log |
| API/worker/report Docker builds | 0 | overnight-backup-docker-build.log |
| Detached Compose refresh and --wait | 0; all ten long-running services healthy | overnight-backup-docker-up.log |

Managed backup is implemented in infrastructure/scripts/managed_backup*.py and
managed_postgres.py. CLI commands and limits are in docs/MANAGED_BACKUP.md.
The first S3 check failed on list-vs-HTTP timestamp precision; comparison now
uses header precision while retaining exact before/after inventory timestamps.
The first restore stopped on MinIO's unsupported public-access-block call.
Portable ACL/policy checks and actual unsigned listing/download rejection replace
that call, not an ignored exception. Later backups correctly rejected constantly
rewritten readiness objects. Exactly three disposable health-probe keys are now
declared as excluded in the manifest; no financial or user-object prefix is excluded.

The latest real archive contains 113 tables and four non-probe objects. Backup,
PowerShell-wrapper verification and isolated restore all returned exit 0:
overnight-managed-backup-create-04.log, overnight-managed-backup-ps-verify.log and
overnight-managed-restore-04.log. SHA-256:
8f9ff62482e5a23a5cb8debc1f4e35831a2ff940e757aef26351036837b2df92.
Restore targets: knk_restore_b8d35d40d1b04133816886f487a2aad7 and
knk-restore-b8d35d40d1b04133816886f487a2aad7. Active data was not a restore target.
The separate integration test proves exact-decimal, snapshot-consistent restore
despite a concurrent source update, and restores all five object classes including
unreferenced retained content. Archive publication was subsequently changed to an
exclusive hard link; the integration test 03 verifies that final behavior.

The live API exposes knk_backup_state{state="VERIFIED"}=1 and all other backup states
zero. Prometheus has loaded the knk-backup rules. This reports the most recent
verification receipt, not a fresh archive checksum on every scrape. Alertmanager
delivery, other dashboards, whole strict mypy and the 27-stage release command
remain incomplete. Generated archives, credentials, screenshots and logs are ignored.

## Compact Chart And Backup Checkpoint

2026-09-12 SGT, ce3def3 plus the saved-form/managed-backup/chart working tree.
Native chart labels retain a 10px font, suppress overlapping ticks and preserve
two-decimal percentage precision. Risk-monitor parent rows retain their minimum
track heights instead of allowing subsequent panels to cover them.

| Command / check | Exit / result | Evidence under logs/ |
| --- | --- | --- |
| Full backend pytest with coverage, run 12 | 0; 1,097 passed, 13 warnings, 342.50s; 10,339/11,816 statements, 87.5% | overnight-backend-12.log / overnight-coverage-12.json |
| Whole first-party Ruff / format | 0 / 0; 266 formatted files | overnight-backup-final-ruff.log / overnight-backup-final-format.log |
| Scoped managed-backup strict types | 0 | overnight-backup-final-types-02.log |
| Whole first-party strict types, run 06 | 1; 1,896 distinct diagnostics / 126 files / 245 sources / nine groups | python-types-06/manifest.json |
| Full frontend units | 0; 256 terminal + 5 shared = 261 | overnight-chart-label-full-units.log |
| TypeScript / lint | 0 / 0 | overnight-chart-label-typecheck-03.log / overnight-chart-label-lint.log |
| Node 22 production build | 0 | overnight-chart-label-build.log |
| Negative-control browser against old build | 1; new risk-panel containment assertion caught the known overflow | overnight-risk-layout-before.log |
| Corrected 1366px/390px visual journeys | 0; two passed, 2.2m | overnight-risk-layout-after.log |
| Final chart frontend Docker build | 0 | overnight-chart-label-docker-build.log |
| Frontend Compose refresh | Wrapper exit 1 despite healthy Docker result; explicit native-exit-code verification returned 0 | overnight-chart-label-docker-up.log / overnight-chart-label-docker-up-02.log |
| Full browser run 07 | 37 passed, zero retries, 8.3m; JSON has zero unexpected/flaky/skipped tests | overnight-browser-full-07.log / overnight-full-07-results.json |

The initial chart test needed the jsdom environment and an explicit value-axis
type guard. Both were corrected without suppressing TypeScript diagnostics.
Direct review of the corrected 1366px overview, performance, risk-monitor and
risk screenshots confirms the label/containment changes. Screenshots are local
evidence only; no all-pages/all-sizes visual-completion claim is made.

## Native DCF Workbook

2026-09-12 SGT, working tree based on pushed commit 955ec9b, branch main.
The workbook builder validates the immutable result and reproduces every saved
scenario before rendering native formulas. Missing source values and invalid
assumptions do not become zero. The generic sixteen-family file test now uses a
real DCF result for its DCF case, rather than relabelling a portfolio fixture.

| Command / check | Exit / result | Evidence under logs/ |
| --- | --- | --- |
| DCF/report targeted tests, run 02 | 0; 57 passed, one warning | overnight-dcf-tests-02.log |
| Added metadata and queued native-model tests | 0; 57 passed in the three-module selection | overnight-dcf-tests-03.log |
| Scoped engine/builder/renderer strict mypy | 0 | overnight-dcf-types-05.log |
| Scoped new unit/integration test strict mypy | 0 after installing pinned OpenPyXL stubs | overnight-dcf-test-types-02.log |
| Whole strict runner 07 | 1; 1,966 distinct diagnostics, 125 files, 248 sources; API 1,107 in 36 files | python-types-07/manifest.json |
| Full first-party Ruff / format | 0 / 0; 269 files formatted | overnight-dcf-full-ruff.log / overnight-dcf-full-format.log |
| Full backend coverage run 13 | 0; 1,110 passed, 13 warnings, 301.79s; 10,601/12,078 covered | overnight-backend-13.log / overnight-coverage-13.json |
| Real Excel full recalculation 01 | 0; three passed, 150.74s | overnight-dcf-excel-01.log |
| Final Excel recalculation 02 | 0; three passed, 88.78s; 264 + 359 + 462 formula checks | overnight-dcf-excel-02.log |
| API/data/quant/report Docker builds | 0 | overnight-dcf-docker-build.log |
| Detached refresh with explicit native exit code | 0; all four refreshed services healthy | overnight-dcf-docker-up.log |
| Live observe-only watchdog check | 0; ten healthy services and successful init | overnight-dcf-health.log |
| PostgreSQL/MinIO report smoke | 0; three formats, private download/checksum and worker-exit persistence | overnight-dcf-report-smoke.log |
| Focused equity/report browser check | 0; three passed, zero retries, 1.2m | overnight-dcf-browser.log |

First-pass strict diagnostics in the workbook builder exposed reused variables
with incompatible types. Descriptive local variables and validated numeric
boundaries corrected them without ignores. Installing OpenPyXL stubs was required
for the new test modules. Existing equity tests still index the now-typed JSON
response without validation; their exposed diagnostics remain part of the total.

Excel tests compare every formula against cached results at 1e-10 relative/absolute
tolerance, then independently edit revenue and invalid WACC/growth assumptions.
The 1-, 5- and 10-year cases cover losses, both terminal methods, initial WC zero,
debt/cash/share overrides, missing prices and calculated WACC. No active workbook
or user's spreadsheet is opened. Original generated source hashes are unchanged.
Final artifacts are under logs/dcf-validation/e38eb804fcf14f4384e4d701ec89fc1f,
c32feb1353b74db9934379f0e250e82a and 606dc82fcc4044709d3adb95db613e2c.

PDFium initially rejected a nonexistent image output directory; explicitly creating
the new directory fixed rendering. Direct review covered scenario summary, source
inputs, one-year/ten-year forecasts, sensitivity table and source sheet. All have
readable nonoverlapping content. The subsequent header-format-only change uses
integer forecast years. This does not certify the other financial-model/deck families.

The PostgreSQL smoke used newly created database knk_report_verify_20260911_190316_79384b.
The active book was not its target. Generated sources, workbooks, PDFs, page images,
databases, logs and credentials remain ignored local evidence.

## Release Runner And Restart Persistence

2026-09-12 03:19-03:33 SGT, branch main, working tree based on pushed 0ad0434.
No active portfolio database, broker credentials or existing user session was reset.

| Command / check | Exit / result | Evidence under logs/ |
| --- | --- | --- |
| Typed DCF consumer regression selection | 0; 58 passed | overnight-dcf-consumer-tests.log |
| Scoped DCF consumer strict types | 0 | overnight-dcf-consumer-types.log |
| Initial runner orchestration tests | 0; 33 passed, 10.57s | overnight-release-runner-tests-01.log |
| Runner + DCF/report affected selection | 0; 91 passed, 17.64s | overnight-release-affected-tests-01.log |
| Final runner/result/seed selection | 0; 54 passed, 22.11s | overnight-release-runner-tests-02.log |
| Scoped runner/result/lifecycle strict types | 0; six files | overnight-release-runner-types-06.log |
| Real PostgreSQL migration/restart attempt 01 | 1; migration passed, cold-start timeout | overnight-postgres-lifecycle-01.log |
| Corrected PostgreSQL migration/restart attempt 02 | 0; two passed, 72.60s | overnight-postgres-lifecycle-02.log |
| First PowerShell release invocation | 1; gates 1-6 passed, gate 7 failed; 1,880 distinct diagnostics / 124 files / 251 sources | overnight-release-command-01.log / release-candidate/20260911T191922Z-b628c07c/manifest.json |
| Expanded PowerShell release invocation | 1; gates 1-6 passed, gate 7 failed; 1,881 distinct diagnostic lines / 124 files / 255 sources | overnight-release-command-02.log / release-candidate/20260911T193027Z-5985dadc/manifest.json |
| Expanded migration gate | 0; 16 SQLite/PostgreSQL tests, no skips, 28.63s | release-candidate/20260911T193027Z-5985dadc/04-01.log / migrations.xml |
| Whole first-party format / Ruff | 0 / 0; 276 formatted files | release-candidate/20260911T193027Z-5985dadc/05-01.log / 06-01.log |
| Frontend TypeScript / lint | 0 / 0 | overnight-release-frontend-types.log / overnight-release-frontend-lint.log |
| Observe-only watchdog | 0; ten healthy services, successful init | overnight-release-health-01.log |
| Full backend coverage run 14 | 0; 1,165 passed, 13 warnings, 300.50s; 10,598/12,078 lines, 87.7463% | overnight-backend-14.log / overnight-coverage-14.json |

The release runner rejects empty gates, pre-existing output directories, changed
source, missing/modified logs, altered command receipts, nonzero exits and missing/
skipped test reports. It records later gates as NOT_RUN and kills only owned process
trees on timeout. Full and visual browser JSON now have independent output paths.
The evidence guard revalidates all preceding commands and hashes before writing
the per-run Markdown receipt. This is not full domain certification.

The first scoped type pass found Windows-only typing of POSIX process-group APIs;
an explicit sys.platform branch resolved it without ignores. A broader seed-test
type command exposed existing transitive application errors plus four Settings
alias constructor diagnostics. Validated Settings input fixed the four new errors;
the existing application errors remain included in the whole type gate.

Restart test 01 failed before liveness because the fresh seed queried existence
for every daily bar over ten years. The empty-security-master guard permits new
PriceBar rows without those redundant lookups. No formula, price, date, volume,
source, natural key, idempotency guard or timeout was weakened. The new history
regression checks all daily rows, an exact first AAPL quote, source lineage and
duplicate absence. Its first attempt accidentally counted its own inspection
query; scoping observation to seed calls fixed the test. Final selection passed.

Restart test 02 used database knk_restore_5ebc0b2df5a74a3ba73f9e277b62045e.
It posts SGD 100,000 capital, ten D05 shares bought at 30, four sold at 35 and a
12 dividend, then checks 99,852 cash, six remaining shares, 20 realised P&L and
NAV = cash + market value. API process IDs 28176/33052 and worker IDs 36512/32516
prove distinct owned processes before/after. Saved transactions and the entire
saved NAV payload match after restart; the session remains valid, exactly one
report remains, and anonymous download returns 401.
Report SHA-256: e8f896806ca4c83b18e47bced0346f4c59b55ced4d68b7e477f2f03546f1ad04.
Full receipt: overnight-postgres-lifecycle-02/test_api_and_worker_restart_pr0/restart-evidence.json.
All owned test processes exited; the existing Docker stack stayed healthy.

Expanded release source SHA-256:
cd22163c765587e0355bf978d248f1859dd0ffddc77911d6a5c8ac90eb5e7ac2.
The one-line difference from the preceding whole type count is an alternate
ordering of missing TypedDict key names in the same existing diagnostic. No new
runner/lifecycle module has a strict error. API-only remains 1,107 errors in 36
files. Gates 8-27 are NOT_RUN in both release invocations, not passing checks.
See RELEASE_CANDIDATE.md for commands, prerequisites and failure semantics.

## Dated Sources, Typed Options and Risk Availability

Baseline a3a5d79 plus working tree, 2026-09-12 SGT. Paths below are under logs/.
No complete release-candidate pass is claimed.

| Check | Native exit / result | Evidence |
| --- | --- | --- |
| FX negative-control regressions before fix | 1; nine failed, two passed | overnight-fx-source-before.log |
| Market-price negative control before fix | 1; three failed, five passed | overnight-market-source-before.log |
| FX/market/history/research/type-gate selection | 0; 46 passed, 7.88s | overnight-source-input-tests-03.log |
| Options dated-specification negative control | 1; four failed, three passed | overnight-options-asof-before.log |
| Options pricing/analytics/API/result tests | 0; 37 passed, 4.64s | overnight-options-types-tests-02.log |
| Exact old/new options comparison | 0; 144 chain and 144 position cases | overnight-options-parity-03.log / verify-options-parity.py |
| Full backend run 15 | 1; 1,184 passed, one failed, 359.79s | overnight-backend-15.log |
| Explicit short-source factor fixture | 0; one passed, 22.54s | overnight-factor-horizon-03.log |
| Full backend run 16 | 0; 1,199 passed, 13 warnings, 376.31s | overnight-backend-16.log / overnight-coverage-16.json |
| Whole strict typing checkpoint 09 | 1; 1,859 distinct diagnostics / 123 files / 257 sources | python-types-09/manifest.json |
| Whole strict typing checkpoint 10 | 1; 1,732 distinct diagnostics / 121 files / 259 sources | python-types-10/manifest.json |
| Scoped strict types, eight changed source/test modules | 0; imports silent only in this scoped check, never in the whole runner | overnight-source-options-scoped-types-01.log |
| Pandas stubs install / pip check | 0 / 0 | overnight-pandas-stubs-install.log / overnight-pandas-stubs-pip-check.log |
| Risk UI regression negative control | 1; four failed, one passed | overnight-risk-empty-before.log |
| Risk UI regression after fix | 0; five passed, 2.79s | overnight-risk-empty-after.log |
| Full frontend unit tests | 0; 261 terminal + five shared tests | overnight-source-options-frontend-unit.log |
| TypeScript / ESLint / Node 22 build | 0 each | overnight-source-options-frontend-types.log / overnight-source-options-frontend-lint.log / overnight-risk-empty-build.log |

The source resolvers now select only observations eligible at the requested date
before applying priority. Future direct FX cannot hide older inverse FX; direction
does not outrank source quality. Invalid selected FX remains INVALID, not demo.
Legacy historical rows remain eligible after newer imported observations arrive.
Explicit preferred sources still exclude alternatives; stale preferred observations
retain their original timestamps and stale flags. Missing volume remains null,
distinct from reported zero, through history and research input validation.

The factor regression previously relied on legacy history being globally hidden.
Restoring valid history correctly made the unpinned 252-day request calculable.
The fixture now explicitly selects the short managed series inside a rolled-back
test transaction, verifies its source and actual length, and keeps the original
252-day/INSUFFICIENT DATA/empty-result assertions. First fixture attempt omitted
the required rule priority; its NOT NULL failure is retained in run 02. Run 03
includes the explicit priority and passes. No runtime history was shortened.

Options contract identity now includes exercise style and UTC expiry clock and is
checked only after excluding future observations. Typed rows preserve all existing
Greek/state/provenance fields. Provider Greeks are not silently substituted with
model Greeks. Missing interest is null; explicit zero interest remains included.
Position tests verify signed owned quantity, explicit zero premium and a known
combined option/equity payoff; nonfinite equity quantities are rejected.

The initial exact comparison caught last-bit rounding changes from converting
NumPy profile values before Python 3.12 summation. Conversion was moved after the
original NumPy accumulation. All 144 chain and 144 position scenarios now match
the committed engine exactly, including provider/calculated, European/American,
missing/zero/positive interest, missing/provided IV and stale/current combinations.
The tolerance was not widened. Full backend run 17 passed 1,199 tests with 13
warnings in 491.91s, exit 0; coverage is 10,823/12,293 statements. Receipt:
overnight-backend-17.log / overnight-coverage-17.json.

The pandas stub update uses the same 2.2.3 runtime target and fixes the upstream
typing of pct_change(fill_method=None). Primary references:
[compatible stub release](https://pypi.org/project/pandas-stubs/2.2.3.250527/) and
[maintained Series declarations](https://github.com/pandas-dev/pandas-stubs/blob/v2.2.3.250527/pandas-stubs/core/series.pyi).
No dependency-wide missing-import suppression was introduced.

Risk charts now state unavailable variance/correlation explicitly, omit missing
heatmap cells without changing coordinates, retain actual zero values and defer
to loading/error states. Existing 1920px overview/risk/options images were reviewed;
new desktop/mobile empty-state screenshots were inspected. Both focused browser
tests passed with zero retries. Runtime UI/API/workers/report refresh returned
healthy, native exit 0 (overnight-source-options-docker-refresh-01.log).

## Ledger Read Race and Factor Latency

2026-09-12 SGT, baseline a3a5d79 plus working tree; full release remains red.

Full browser run 08 exposed an initial query/mutation race. The POST returned 201,
but the only trade-list GET started before the save. TanStack Query 5.62.8 keeps
an in-flight initial read when invalidated with no existing data. The dialog now
explicitly cancels each affected read before invalidation. Five deterministic
negative-control tests failed before the fix; all 18 transaction-entry tests pass
after, including late-response rejection and exact persisted transaction identity.
Logs: overnight-ledger-refresh-before.log / overnight-ledger-refresh-after.log.

The browser short-history assertion now explicitly selects the short managed demo
source in its isolated database and restores every original source rule in finally.
The 252-day, INSUFFICIENT DATA and empty-row assertions remain intact. No real
source rules or live portfolio data are changed by this fixture.

Factor profiling found 19 resolver constructions and 107,597 ORM materializations
per request (13.679s instrumented). One shared resolver removes duplicate reads;
the six-security SQL-count fixture now performs one price-history SELECT rather
than eight. Both query-count tests failed before the fix. The affected selection
then passed 29 tests, exit 0 (overnight-factor-reads-after.log).

Repeated pandas row objects were the other major cost. Pairwise masks and average
ranks are prepared once; stable sorting, NumPy correlation, quantile means and
turnover preserve the previous calculation. No history/horizon/tolerance was
shortened. Eighteen complete result comparisons cover all six factors across full,
missing/tied/infinite and insufficient data. Exact comparison run 03 exits 0;
complete 800-date calculations improved from multi-second runs to subsecond runs.
Evidence: overnight-factor-statistics-parity-03.log / verify-factor-statistics.py.

Permanent direct-pandas, missing-benchmark and SQL-count tests: 22 passed, 5.29s
in overnight-factor-optimized-tests-02.log. The first new missing-data fixture also
removed the benchmark's entire rolling history and correctly returned no beta;
it now retains the benchmark for cross-section checks and separately asserts the
missing-benchmark empty state. Scoped strict types for factor statistics and its
test module pass (overnight-factor-scoped-types-02.log).

Current frontend units: 266 terminal + five shared = 271, native exit 0
(overnight-ledger-factor-unit.log). TypeScript, ESLint, Ruff and formatting pass.
The Node 22 production build passed (overnight-ledger-factor-build.log).
Whole strict types checkpoint 12 exits 1: 1,667 distinct diagnostic lines in 119
files, 260 inventoried sources; API 913 errors in 33 files. Checkpoint 11 had 1,732
diagnostics. No global type suppressions were added. Backend run 18 passed 1,214
tests with 13 warnings in 469.49s, native exit 0. Coverage: 10,871/12,341 statements.
Receipts: overnight-backend-18.log / overnight-backend-18.xml /
overnight-coverage-18.json. The three affected browser journeys passed, native exit
0, zero skipped/flaky/retries, 2.7m. Their durations were 19.7s (manual ledger),
1.1m (operating desks including all sizes and explicit factor source), and 51.1s
(saved alpha/model/Monte Carlo and the interactive 21-day volatility factor).
Receipts: overnight-ledger-factor-focused-01.log /
overnight-ledger-factor-focused-01-results.json. This is a focused pass, not a
replacement for the next complete browser run.

Full browser run 08 finished exit 1: 36 passed, three failed, zero skipped/flaky,
23.3m. JSON receipt: overnight-full-08-results.json. All five viewport sweeps
passed, but the full suite did not. The exact failing journeys are manual ledger
audit persistence, operating desks/short factor history, and saved quant runs/
interactive Factor Lab. The corrected build is under targeted verification.
Additional original screenshots inspected: macro at 1366px and GEX at 2560px.
Secret scan passed for 587 text files with zero findings; the broker-action scan
passed. Both receipts have prefix overnight-ledger-factor-.

## Local Agent Recovery and Paper Reader Contracts

2026-09-12 SGT, baseline 364503e plus the agent contract batch.

Archive intent is committed before a local rename. Interrupted acknowledgements
resume the recorded target even after a month change or process restart. Missing
or changed local bytes cannot be acknowledged as archived. Existing SQLite queue
records receive an additive archive_path column and are preserved. Upload and
archive responses are validated before changing local state; invalid server
origins are rejected without including credential fragments in errors.

Recovery negative controls: 15 failed / three passed before implementation.
The expanded recovery suite passes 23 tests, native exit 0 in
overnight-local-agent-recovery-after-02.log. Paper reader negative controls: five failed /
two passed. All 30 combined new tests then passed in 7.92s, native exit 0;
the receipt is overnight-agent-reader-after.log. Tests use temporary files,
mock HTTP transport and recorded SDK-shaped values, not a broker connection.

Reader settings and responses are typed. Nonpositive/out-of-range client IDs are
rejected before constructing the SDK client. This excludes client ID zero's
special order-binding behavior in the pinned SDK. Missing option/futures
multipliers are rejected; the stock identity multiplier and actual zero cash
remain valid. Missing marks remain unavailable, not zero.

requirements-dev.txt now installs the existing pinned broker requirements,
including ib_async 2.1.0, so SDK contract tests are repeatable. Installation and
pip check exit 0. Both agent source files and both new test files pass strict
types; Ruff and formatting pass. Whole strict checkpoint 13 remains red:
1,619 distinct diagnostic lines in 117 files, 262 inventoried sources. The
local-agent distribution has zero diagnostics; API remains 913 in 33 files.

Full backend 19: 1,244 passed, 13 warnings, 447.09s, native exit 0. Coverage is
10,875/12,341 statements (88.1209%), 1,466 missing. Receipts:
overnight-backend-19.log / overnight-backend-19.xml /
overnight-coverage-19.json. These results precede the separate ASGI concurrency
fix under investigation. Browser run 09 is still active and has exposed SQLite
lock errors during workspace persistence and factor reads. No full browser or
27-stage release pass is claimed for this checkpoint.

## ASGI Concurrency and Scoped Status Lookup

Baseline f0d92e3 plus working tree, 2026-09-12 SGT.

Full browser 09 completed with 38 passed / one failed, zero retries, 20.7m.
All five viewport sweeps passed. The quant journey's trace records a 14.18s
factor request ending in HTTP 500, and the API log records SQLite lock failures
in workspace commits, factor queries and authentication reads. The trace and
failure screenshot are retained under logs/overnight-full-09-failure; the JSON
receipt is overnight-full-09-results.json. This was not a clean browser pass.

The asynchronous middleware previously performed synchronous initialization and
authentication database work on the event loop. These checks now run in the
thread pool, with each SQL session opened and closed within that call. The loop
can finish other responses and release their sessions during a blocked read.
Access checks, private cache headers and origin rejection are unchanged. A typed
session payload preserves the existing optional email/role response fields.
Two deterministic blocked-loop tests failed before the fix; the concurrency,
authentication and telemetry selection then passed 29 tests, native exit 0.
Receipts: overnight-middleware-before.log / overnight-middleware-after.log.
No database timeout, journal mode, test timeout or financial tolerance was changed.

The agent now requests pending file identities in batches of at most 100. The API
keeps its default 500-file listing but permits bounded, ownership-scoped lookup
of older IDs. Six status regressions failed before the fix, with two already
passing. Additional negative controls reproduced missing-record starvation and
acceptance of a changed hash in a nonterminal status. Missing remote records now
retain their state and enter backoff while available records continue. Unexpected
or duplicate response identities and changed hashes cannot advance local state.
Revoked tokens, absent tokens and tokens without status scope remain rejected.

Final focused selection: 71 passed, three warnings, 32.65s, native exit 0 in
overnight-status-middleware-focused-03.log. This includes all 12 status tests,
23 archive tests, seven paper-reader tests and 29 middleware/auth/telemetry tests.
Whole Ruff and formatting pass (285 Python files). Whole strict checkpoint 14
still fails: 1,608 distinct diagnostic lines in 117 files, API 901 in 33 files.
Both local-agent sources and both newly added test modules have no diagnostics.
No type ignores or untyped replacements were added.

Intermediate backend 20 passed 1,251 tests in 446.23s. Status tests were added
after that invocation collected its tests, and source line locations changed
during the run, so its coverage is not used as final evidence. Full backend 21
passed 1,263 tests, 13 warnings, 447.63s, native exit 0. Coverage is 10,901/12,366
statements (88.1530%), 1,465 missing. Receipts: overnight-backend-21.log /
overnight-backend-21.xml / overnight-coverage-21.json. Application sources were
unchanged during that invocation. The later local-backup-tool batch has separate
focused verification and is not claimed as part of that complete run.
Full browser 10 is still active. Production Docker has not yet received the ASGI
change. Overall release status remains open.

Additional direct visual review: equity 1366px, portfolio and data-drop 1440px,
and quant-dashboard 1920px. Tables, pane boundaries and toolbar controls were
inspected; this does not certify all snapshots or replace the strict visual gate.

## Local Backup Manifest Contracts

Baseline 667c0a6 plus working tree, 2026-09-12 SGT. The ASGI/status batch is pushed.
Local archive manifests now validate version, timestamp, encryption/sensitivity,
file sizes/hashes and table counts before creating a restore directory. Duplicate
JSON keys are rejected rather than overwritten. Existing valid v1 archives retain
their format and SQLite snapshot/hash/integrity verification. The three direct
CLI entrypoints resolve their package imports from unrelated working directories.
No active database, object store, credential or production volume was changed.

Negative controls: nine failed / two passed in
overnight-local-backup-manifest-before.log. Final combined selection: 23 passed,
one warning, 4.44s, native exit 0 in overnight-local-backup-manifest-after-03.log.
Coverage of infrastructure.scripts.backup_archive is 176/201 statements (87.5622%),
25 missing, in overnight-local-backup-coverage.json. The earlier after-02 invocation
used an incorrect coverage target; its empty coverage is not accepted as evidence.
Six affected source/test files pass strict mypy in overnight-local-backup-types-04.log.
Whole Ruff and format checks pass after the final test annotations. Backend 21
preceded this batch; no newer complete backend pass is claimed here.

Browser 10 is still active and has reproduced the quant journey failure at the
unchanged factor-table assertion. Its API log contains workspace commit and read
lock errors. The middleware fix closes the independently reproduced event-loop
block, but does not close this database contention. A read-only profile against
browser 09's retained database takes 4.50s, with 3.19s in price-resolver loading and
0.19s in factor statistics. Three concurrent read-only calls take 8.52s, 11.26s and
12.16s (overnight-factor-profile-03.log / overnight-factor-concurrent-01.log).
No journal mode, timeout, financial tolerance or browser assertion was changed.

## Recovery Probes and Migration Contracts

Baseline a7c9368 plus working tree. Missing database paths can no longer create
an empty SQLite file during inventory. Recovery inventories reject databases
without business tables, close connections, and represent absent job tables as
unavailable rather than zero. Malformed API readiness JSON produces NOT_READY
instead of crashing. Receipt output cannot overwrite the source database,
including an existing same-file alias. Reference inventories are validated and
preservation checks use explicit exceptions, so Python -O cannot remove them.

Initial recovery negative controls: eight failed / four passed. An additional
source-output collision test failed against the intermediate code and now passes.
Final recovery/backup selection: 45 passed, one warning, 3.66s, native exit 0 in
overnight-recovery-probes-expanded-after.log. Five selected source/test files pass
strict types in overnight-recovery-probes-types-02.log. These tests modify only
temporary fixture databases; no user database was used as an output target.

Migration helpers expose SQLAlchemy schema-item contracts, and revision 0002
retrieves the same registered Table instances through typed metadata. Migration
ordering, column definitions, keys and constraints are unchanged. Missing URLs
fail explicitly; a configured URL is still used when the environment is unset.
All eight migration modules pass strict types. Final migration selection:
19 passed, one warning, 37.65s, native exit 0, including the real isolated
PostgreSQL upgrade/downgrade preservation test. Receipts:
overnight-migration-typed-02.log / overnight-migration-typed-02.xml.

Whole strict checkpoint 15: 1,576 distinct diagnostics in 109 files, 267 sources.
Checkpoint 16 after migration cleanup: 1,564 diagnostics in 104 files, 267 sources.
No remaining diagnostic originates in repository-tools; that invocation remains
red because strict checking also reports its imported API dependencies. API has
901 diagnostics in 33 files. No ignores, missing-import suppression or broad Any
annotations were added. Whole Ruff/format, secrets and no-execution checks pass.

Browser 10 completed with 37 passed / two failed / zero retries in 23.0m. The
saved-quant factor failure was followed by a backtest page timeout; all five
viewport sweeps passed. Both failure traces/screenshots are retained under
logs/overnight-full-10-failures. This run used the pre-projection API process and
pre-debounce frontend build. A fresh Node 22 frontend build now passes with the
explicit local-test API origin; a prior invocation correctly failed for missing
deployment configuration. The rebuilt targeted run has passed the saved-quant
journey; its remaining test and the new overlap regression are not yet certified.
Full backend 22 is active; backend 21 is not evidence for these later changes.

## Factor Request Overlap and Price Projection

Baseline 483171e plus working tree. Factor Lab coalesces controls after 300ms,
cancels obsolete queries when their key changes, and hides results belonging to
previous inputs. Explicit zero costs are retained. The market-price resolver
selects scalar legacy-history columns instead of hydrating an ORM identity for
every bar. It retains the existing date/source filters, precision, provenance,
ordering and missing-volume behavior. No database journal mode or timeout changed.

The projection regression failed before the change and passes after it. The
affected market/FX/factor selection passes 42 tests, native exit 0, 10.43s in
overnight-price-projection-focused.log. A comparison against a7c9368's implementation
has exact equality for 54,241 observations and all 18 factor-result cases across
six factors and three lookbacks (overnight-price-projection-parity.log).
Three concurrent read-only calls now take 5.09s, 6.51s and 8.34s versus the earlier
8.52s, 11.26s and 12.16s; timings are measurements, not relaxed acceptance limits.

Four new UI unit tests cover coalescing, zero cost, stale-result hiding, immediate
abort and unmount cleanup. All 270 terminal unit tests pass on Node 22 in 68.90s.
TypeScript, ESLint, the Node 22 production build, Ruff and formatting pass.
Receipts: overnight-factor-ui-full.log / overnight-factor-ui-types.log /
overnight-factor-ui-lint.log / overnight-factor-next-build-02.log.
Initial UI test attempts lacked a mock for a second chart and did not provide a
valid negative control; final tests mock both charts and exercise real query state.

The rebuilt operating/quant selection passes four browser tests, zero retries,
2.5m, native exit 0. The added deliberate overlap/reload test passes independently,
zero retries, 39.0s total (17.6s test time). Both API logs have no database-lock or
HTTP 500 entries. Receipts: overnight-factor-projection-browser-results.json /
overnight-factor-overlap-results.json. Desktop 1440px and mobile 390px factor
screenshots were inspected; no overlapping controls or document-width overflow
was observed. This does not certify the entire terminal screenshot set.

Full browser 11, now 40 tests, and backend 22 remain active. No complete current
browser pass or 27-gate release pass is claimed. The persistent Docker image has
not yet been refreshed with this batch.

## Backend 22, Local Refresh and Alpha Contracts

Full backend 22 completed: 1,300 passed, 13 warnings, 427.31s, native exit 0.
Coverage is 10,901/12,366 statements (88.1530%), 1,465 missing. Receipts:
overnight-backend-22.log / overnight-backend-22.xml / overnight-coverage-22.json.
Application source remained unchanged during this run. Its coverage and test
count do not include the subsequent alpha-statistics edits or added library tests.

Docker build and --no-deps/--no-build health-gated refresh for 6edb4e2 both exit 0.
API, data/quant workers, report engine and terminal were refreshed without changing
the database or storage volumes. All ten services are HEALTHY and MinIO init is
SUCCEEDED in overnight-factor-watchdog.log. /overview responds through the private
sign-in route on port 3001. Receipts: overnight-factor-docker-build.log /
overnight-factor-docker-up.log. Python image exports completed before alpha source
edits began; the later alpha batch is not claimed in these images.

The alpha-statistics boundary now has explicit regression, coefficient, interval,
rolling and availability contracts. Scalar finite checks retain positive/negative
zero and keep nonfinite observations unavailable. The CAPM-specific Jensen field
is composed in the API response without changing its previous JSON output.
Existing numeric tolerances and financial assertions were preserved; new non-null
assertions make existing successful-result assumptions explicit.

Local stubs cover the consumed NumPy surface of the installed statsmodels 0.15.0,
verified against actual signatures and an instantiated OLS/HAC result. Runtime
stub verification passes for the declared public surface; unrelated library APIs
are outside these partial stubs. scipy-stubs 1.14.1.6 was added for the installed
Windows SciPy 1.14.1, with no runtime NumPy/SciPy change. Installation and pip check
pass. An initial test annotation lacked postponed evaluation and failed collection;
adding the future import fixed it without weakening any test.

Final alpha/statistical-library/API selection: 20 passed, one warning, 6.65s,
native exit 0 in overnight-alpha-focused-03.log. Five source/test/stub files pass
strict types in overnight-alpha-types-03.log. Four independent tests reconstruct
Bartlett HAC covariance, finite-sample correction, standard errors, t statistics,
p-values and confidence intervals using explicit matrix calculations. Runtime
arrays are float64 with verified shapes. Nine full-analysis and four unavailable
cases have exact old/new result equality in overnight-alpha-parity.log.

Whole strict checkpoint 17 still fails: 1,535 diagnostics in 102 files, 270 source
files inventoried. API is 877 diagnostics; alpha_statistics has none. Full browser
11 remains active, with both formerly failing quant journeys now passed.

Observed dependency gap: Windows NumPy/SciPy are 2.2.1/1.14.1, while the existing
Docker environment is 2.5.3/1.18.1. Both carry statsmodels 0.15.0. The shared source
tests and exact same-runtime comparisons do not establish cross-runtime parity;
scientific dependency alignment and fresh verification remain open.

## Browser 11 And Clean Scientific Environment

2026-09-12 SGT, source 6edb4e2 for browser 11; current HEAD 9c7428c plus the
numerical dependency/statement typing batch for subsequent checks.

`corepack pnpm dlx node@22 node_modules/@playwright/test/cli.js test tests/e2e
--workers=1 --retries=0` with isolated run ID overnight-full-11 completed with
native exit 0: 40 passed, no skipped/unexpected/flaky results, 975.354 seconds.
Start: 2026-09-11T21:32:34.267Z. Receipt: overnight-full-11-results.json; console:
overnight-browser-full-11.log. API log has no database-lock or HTTP 500 entries.
All five viewport sweeps and the added factor overlap journey passed in this
single invocation. This does not certify later source changes or all 27 gates.

A new `.venv-release` uses Python 3.12.10 without system-site-packages. The previous
environment is preserved. Installation from API, dev, local-agent and report-engine
requirements returned 0 (overnight-clean-install-01.log); pip check returned 0.
API and quant worker now explicitly pin NumPy 2.5.3 / SciPy 1.18.1, the already
observed Docker runtime versions; scipy-stubs is matched at 1.18.1.0. Three new
tests enforce service pin consistency, installed numeric versions and stub/runtime
alignment. No numerical tolerances were changed.

Clean-environment scientific selection (dependency, alpha, statsmodels contract and
equity financial tests): 40 passed, one warning, 28.78s, exit 0 in
overnight-clean-scientific-01.log. SQLite/PostgreSQL migration selection: 19 passed,
one warning, 34.15s, exit 0 in overnight-clean-migrations.log/xml. An observe-only
watchdog check returned 0 at 2026-09-11T21:54:57Z: ten healthy services and successful
MinIO initialization, no restart action. Full backend 23 is still running.

Statement rows now validate their JSON shape before filtering/TTM aggregation.
Scalar numeric conversion remains explicit, lineage and original inputs remain
unchanged, and missing/zero denominator semantics are retained. Comparable outputs
have a concrete typed result. The first strict check caught a reused comprehension
variable name and an unannotated adapter; both were fixed without ignoring errors.
Three affected files then pass strict mypy. The expanded affected suite passes
33 tests, three warnings, 24.30s (overnight-equity-statements-02.log), exit 0.
1,500 deterministic old/new statement, ratio and comparable outputs have exact
equality in overnight-equity-statements-parity.log. New tests also reject malformed
rows/compound numeric values and assert nonmutation and lineage retention.

Whole strict checkpoint 18 returned 1: 1,489 distinct diagnostics in 100 files,
271 sources across all distributions. API: 838 diagnostics in 31 files. Receipts
are in overnight-whole-types-18/. Current Ruff and format checks returned 0 in
overnight-clean-ruff.log / overnight-clean-format.log. Full release remains open.

Full clean-environment backend 23 then completed: 1,330 passed, 122 warnings,
381.48s, native exit 0. Command: `.venv-release/Scripts/python.exe -m pytest
tests/sprint services/api/tests --cov=services/api/app --cov-report=term
--cov-report=json:logs/overnight-coverage-23.json
--junitxml=logs/overnight-backend-23.xml -q`, with isolated database/object/coverage
paths. Coverage: 10,959/12,424 statements, 88.2083065%, 1,465 missing, 23 excluded.
Warnings are deprecations in pandas/NumPy timedelta conversion, Starlette/AnyIO
and the existing FastAPI startup hook, not failed financial assertions.

All 19 full-browser-11 mobile screenshots were inspected. Desktop 1366px review
of alpha/equity/quant revealed two additional defects: collapsed Equity top-row
panels and rounded-to-zero nonzero alpha coefficients/errors. New research-layout
browser tests reproduce both against the prior built frontend (two failed,
native exit 1, zero retries). The Equity coverage table is hidden; alpha's
rendered coefficient becomes zero. Traces/screenshots are preserved under
logs/overnight-research-layout-before-artifacts. No baseline was auto-accepted.
Corrective frontend work is separate from the verified backend batch above.

## Research Layout And Statistical Precision

2026-09-12 06:00-06:15 SGT, f381f8e plus research UI worktree. Equity now has
explicit two-row desktop / three-row mobile grid tracks. Alpha coefficients,
standard errors, p-values and confidence bounds use six significant digits,
preserving true zero, missing values and very small nonzero values. Stress chart
tracks reserve room for the canvas, axis labels and source footer.

| Command / check | Exit | Evidence |
| --- | --- | --- |
| Node 22 Playwright research-layout against old build, zero retries | 1 | overnight-research-layout-before.log/json: two failures reproduce hidden Equity table and nonzero alpha rendered as zero; traces retained |
| Node 22 Vitest financial-format selection | 0 | overnight-statistical-format-unit.log: 72 passed, including 21 new precision cases |
| Terminal TypeScript / ESLint | 0 each | overnight-research-ui-types.log / overnight-research-ui-lint.log |
| Node 22 Vitest terminal suite from repository root | 1 | overnight-research-ui-full.log: wrong cwd omitted terminal Vitest JSX configuration; harness invocation error, not a product negative control |
| Node 22 Vitest terminal suite from apps/terminal-web | 0 | overnight-research-ui-full-02.log: 291 passed in 22 files, 62.95s |
| Node 22 Vitest shared suites | 0 | overnight-research-shared-unit.log: five passed in two files |
| Node 22 Next build with explicit local test API environment | 0 | overnight-research-next-build.log |
| Node 22 Playwright research-layout after Equity/alpha fixes, zero retries | 0 | overnight-research-layout-after.log/json: two passed |
| Node 22 Playwright stress chart containment before CSS fix, zero retries | 1 | overnight-stress-chart-before.log/json: canvas/footer geometry fails; trace retained |
| Node 22 Next build including stress correction | 0 | overnight-research-next-build-02.log |
| Node 22 Playwright all three research-layout cases, zero retries | 0 | overnight-research-layout-final.log/json: three passed in 1.0m; 21.3s Equity, 12.8s alpha, 6.6s stress |
| Broker-action scan | 0 | overnight-research-no-execution.log |
| Clean-environment OpenAPI generation | 0 | overnight-clean-openapi.log: 170 paths, 77 schemas |
| Observe-only watchdog | 0 | overnight-research-watchdog.log at 2026-09-11T22:09:25Z: all ten services healthy; MinIO initialization succeeded |

Corrected Equity screenshots were reviewed at 1366/1440/1920/2560/390px; alpha
and stress at 1366/390px. Evidence remains local under logs/research-screenshots.
No visual baselines were accepted, and the full visual matrix is not certified.
The persistent Docker stack still carries 6edb4e2 until the next explicit refresh.
Full browser 12 and all 27 release stages remain unverified for this batch.

## Broker Snapshot Contracts And Local Refresh

2026-09-12 SGT, 68698d8 plus broker worktree. The Docker build and health-gated
refresh use 68698d8, before the broker edit. Both commands returned native 0:
`docker compose --env-file .env.compose.local -p knk-final-local build api
worker-data worker-quant report-engine terminal-web`, followed by `up -d
--no-deps --no-build --wait --wait-timeout 240` for those five services. Logs:
overnight-research-docker-build.log / overnight-research-docker-up.log. Deployed
/app/app/broker_api.py SHA256 equals git 68698d8's source. No database or volume
reset. Observe-only watchdog returned 0 at 2026-09-11T22:20:42Z; all ten long-running
services healthy and MinIO init succeeded. /overview reaches /login with HTTP 200.

Broker input/output annotations are now explicit. Stored fills validate shape and
account fingerprint before approval; invalid sides cannot fall through to SELL.
Typed holdings preserve missing FX and reject invalid financial values. A complete
total is unavailable when any component is missing, but an actual empty/zero total
remains zero. Approval still requires authenticated manual action and recorded
commission. No broker order method was introduced.

| Command / check | Exit | Evidence |
| --- | --- | --- |
| Clean Python pytest broker views + existing agent tests | 0 | overnight-broker-contracts-01.log: seven passed, three warnings, 42.48s |
| Expanded persisted-fill contracts + prior selection | 0 | overnight-broker-contracts-02.log: 32 passed, three warnings, 10.31s |
| Financial-value guards + broker/ledger revisions | 0 | overnight-broker-contracts-03.log: 62 passed, three warnings, 18.75s |
| Final consumer-typed same selection | 0 | overnight-broker-contracts-04.log: 62 passed, three warnings, 13.36s |
| Strict broker source + new contract tests | 1 then 0 | overnight-broker-types-02.log caught three test imports through a non-exporting module; corrected to the defining module in -03/-04 |
| Strict broker source + both sprint test files | 0 | overnight-broker-types-05.log: three files, no errors |
| Ruff changed source/tests | 0 | All checks passed |
| OpenAPI generation | 0 | overnight-broker-openapi.log: 170 paths, 79 schemas; all three broker routes present |
| 200 deterministic old/new broker views | 0 | overnight-broker-view-parity.log; signed positions, multipliers, zero NAV and missing FX, exact dictionary equality and input nonmutation |
| Whole first-party strict checkpoint 19 | 1 | overnight-whole-types-19/: 1,441 distinct diagnostics, 99 files, 272 sources; API 738 in 30 files |

The type checkpoint exposed new test consumer narrowing needs; the affected broker
view and approval assertions now validate their JSON shape without weakening the
financial assertions. Checkpoint 20 is running after those fixes. Existing broader
agent/reconciliation typing remains open. Full backend/browser gates are next.

## Research Desk Contracts And Browser 12 Follow-Up

2026-09-12 06:24-06:38 SGT, c906ef0 plus worktree. Browser 12 loaded the c906ef0
API and the earlier final research frontend build before these edits. It remains
active with zero retries; no complete browser pass is claimed.

| Command / check | Exit | Evidence |
| --- | --- | --- |
| Whole strict checkpoint 20 | 1 | overnight-whole-types-20/: 1,372 diagnostics, 98 files, 272 sources |
| Initial candidate/operating pytest | 0 | overnight-desks-tests-01.log: seven passed, three warnings, 38.81s |
| Research contracts/candidate/operating/equity pytest | 0 | overnight-desks-tests-02.log: 39 passed, three warnings, 17.42s |
| Focused strict source/tests | 0 | overnight-desks-types-02.log: two files |
| Ruff and formatting affected Python | 0 each | All checks passed; three files already formatted |
| Read-only populated-view parity attempt | 1 | overnight-desks-parity.log: valuation cache miss attempted a write and SQLite correctly rejected it; active test data unchanged |
| Populated-view parity on SQLite in-memory backup | 0 | overnight-desks-parity-02.log: exact Quant (2,674,839 serialized characters) and Equity (13,268 characters) equality; only in-memory copy writable |
| Whole strict checkpoint 21 | 1 | overnight-whole-types-21/: 1,281 diagnostics, 97 files, 273 sources; API 647 in 29 files |
| Incorrect broker-action script path | 1 | MODULE_NOT_FOUND for scripts/check-no-execution.mjs; no scanner pass inferred |
| Actual package-declared broker-action scan | 0 | node tests/security/no-execution-methods.mjs; overnight-broker-no-execution.log |
| Timestamp unit tests | 0 | overnight-timestamp-tests.log: 12 passed; missing/malformed values remain Not observed, UTC/offset conversion retained |
| Frontend TypeScript | 0 | overnight-health-ui-types.log; default Node 20 CLI emitted engine warning, command passed |

The research desk validates persisted result rows, OOS scalars and dataset maps.
Candidate reviews validate saved history before state mutation. The existing
financial and chronological assertions remain intact. A new type annotation on
run_payload exposes one history-list variance error to fix after backend 24;
checkpoint 21 is not a static-quality pass.

Browser-12 ledger correction failed only at the direct GET after confirmed revision
2/history. Trace response end 174660.791ms and next GET start 180660.327ms yield
5,999.536ms idle time. Node 22.23.2 reports Keep-Alive timeout=5; its documented
one-second server buffer gives a six-second close boundary. This timing strongly
indicates connection reuse racing server expiry, rather than a rejected ledger
write. No retry was added. Startup is changed to --keepAliveTimeout 70000 in the
package script, Windows launcher and browser harness; new browser verification is
pending. References: [Node HTTP timeout buffer](https://nodejs.org/api/http.html#serverkeepalivetimeoutbuffer)
and [Next production keep-alive guidance](https://nextjs.org/docs/app/api-reference/cli/next).

Further 1366px screenshots reviewed: data drop/catalogue, health, Excel/Deck,
macro, portfolio and GEX. Health showed Invalid Date for unobserved provider/worker
times; the typed formatter correction is pending a rebuilt browser check. GEX
million-scale negative y-axis labels appear clipped and remain an open visual
task. Neither observation was hidden by accepting a visual baseline.

## Completed Backend And Browser Checkpoint

2026-09-12 06:41-06:47 SGT, c906ef0 plus research-desk worktree.

| Command / check | Exit | Evidence |
| --- | --- | --- |
| Clean Python full pytest tests/sprint services/api/tests with API coverage | 0 | overnight-backend-24.log/xml: 1,396 passed, 122 warnings, 487.64s; overnight-coverage-24.json: 11,080 / 12,509 statements (88.5762%) |
| Full Node 22 Playwright tests/e2e, one worker, zero retries | 1 | overnight-browser-full-12.log / overnight-full-12-results.json: 42 passed, one ledger ECONNRESET, 16.7m; all five viewport sweeps passed; trace copied to overnight-full-12-failures |
| Follow-up pytest desk/candidate/equity including history serialization | 0 | overnight-desks-tests-03.log: 35 passed, one warning, 6.06s |
| Focused mypy --strict --follow-imports=silent --explicit-package-bases desks_api and new desk tests | 0 | overnight-desks-types-03.log: two files; imported dependencies are not certified by this focused check |
| Whole strict checkpoint 22 | 1 | overnight-whole-types-22/: 1,281 distinct diagnostics, 97 files, 273 sources; API 646 in 29 files |
| Changed Python Ruff / format --check | 0 each | three files already formatted, no lint errors |
| Secret / no-execution scans | 0 each | overnight-desks-secrets.log / overnight-desks-no-execution.log |
| Old-build health negative + connection/correction browser selection | 1 | overnight-health-negative-01.log/json: two passed, health failed on Invalid Date; zero retries, 57.3s; trace preserved in overnight-health-negative-01-failures |
| Full terminal Vitest from apps/terminal-web on Node 22 | 0 | overnight-health-full-ui-tests.log: 303 passed, 23 files, 95.78s |
| Frontend TypeScript / ESLint | 0 each | overnight-health-ui-types.log / overnight-health-ui-lint.log |
| Node 22 Next production build with test API environment | 0 | overnight-health-next-build.log |

The history list copy follows backend 24 and has separate follow-up test evidence.
Whole checkpoint 22 removes its variance diagnostic but another distribution now
reports an existing services.py PriceProvenance default error. That diagnostic is
retained; the whole gate remains red. The rebuilt focused browser selection is
active, not yet a pass. No financial tolerance, security assertion or retry count
was weakened. Persistent Docker remains on 68698d8 with all data preserved.

2026-09-12 06:45-06:46 SGT: rebuilt Node 22 focused Playwright selection returned
native 0, three passed, zero retries, 41.3s. Ledger correction 10.7s, production
idle-boundary 6.1s, missing health times 3.9s. Evidence:
overnight-health-positive-01.log / overnight-health-positive-01-results.json.
Both corrected health screenshots (1366px and 390px) were inspected from
logs/health-screenshots; table content remains horizontally scrollable on mobile,
with no document overflow. Research contracts were pushed as 74fe9e5.
The complete browser suite and later strict/deployment gates remain open.

## Simulation Input Contracts And Health Deployment

2026-09-12 06:48-07:00 SGT, cbb2cf1 plus simulation worktree. Existing seeded
NumPy calculations are unchanged. Persisted input shape is validated before
simulation; malformed dates, missing returns and uncompleted backtests cannot
become eligible samples. Backtest pinning preserves dataset IDs, exact daily FX
rate strings, prior-fixing cutoffs, provenance and original request parameters.

| Command / check | Exit | Evidence |
| --- | --- | --- |
| Node 22 Docker production build | 0 | overnight-health-docker-build.log: all five application images built |
| Health-gated Docker up, then final up after completed image export | 0 each | overnight-health-docker-up.log / overnight-health-docker-up-final.log; initial up began while frontend image export was finishing, so only final up is deployment evidence |
| Observe-only watchdog | 0 | overnight-health-watchdog.log, 2026-09-11T22:53:08Z: ten healthy services and successful MinIO init |
| HTTP /overview and deployed source hash checks | 0 | HTTP 200 after login routing, Keep-Alive timeout=70; container Monte Carlo/desks source hashes equal cbb2cf1 |
| Clean pytest Monte Carlo/backtest engine | 0 | overnight-research-input-tests-01.log: 22 passed, one warning, 30.60s |
| Expanded pinning/research/portfolio tests | 0 | overnight-research-input-tests-02.log: 42 passed, seven warnings, 48.80s |
| All affected simulation/research/portfolio tests | 0 | overnight-research-input-tests-03.log: 59 passed, seven warnings, 51.60s |
| Final consumer regression pytest | 0 | overnight-research-input-tests-04.log: ten passed, one warning, 10.71s |
| Strict focused simulation source/new tests | 0 | overnight-research-input-types-02.log: three files; -03.log: four files after existing test annotation correction; imports silent only in these focused checks |
| Exact prior/current Monte Carlo comparison | 0 | overnight-mc-parity.log: 80 seeded cases across four methods, nine persisted backtest pin/result pairs; prior source cbb2cf1 |
| Exact prior/current backtest input comparison | 0 | overnight-backtest-pin-parity.log: eight populated maps including daily FX/provenance; source database and objects read-only, comparison database in memory |
| Whole strict checkpoint 23 | 1 | overnight-whole-types-23/: 1,263 diagnostics, 95 files, 274 sources; API 630 in 27 files |
| Whole strict checkpoint 24 | 1 | overnight-whole-types-24/: 1,260 diagnostics, 94 files, 274 sources; three test consumer diagnostics corrected, no suppressions added |
| Changed-source Ruff | 1 then 0 | Literal import was accidentally placed below test definitions (seven diagnostics); moved to imports before test execution; all six files then pass |
| Changed-source format check | 0 | six files already formatted |
| Secret and broker-action scans | 0 each | overnight-simulation-secrets.log / overnight-simulation-no-execution.log |

Backend 25 is active on the final simulation source. Browser 13 uses the cbb2cf1
frontend and its initially loaded API, with later worker processes able to import
the simulation worktree; it is not a uniform final-release source certification.
The new options-axis canvas regression is added but has not run yet. No visual
baseline was accepted. Cloud and live-provider verification remain external.

## Macro Provenance And GEX Label Containment

2026-09-12 07:01-07:14 SGT, 50c1b60 plus frontend worktree.

| Command / check | Exit | Evidence |
| --- | --- | --- |
| Clean full backend pytest with API coverage | 0 | overnight-backend-25.log/xml: 1,427 passed, 123 warnings, 496.94s; overnight-coverage-25.json: 11,148/12,562 statements (88.7438%) |
| Full Node 22 Playwright, one worker, zero retries | 0 | overnight-browser-full-13.log / overnight-full-13-results.json: 45 passed, zero failed/skipped/flaky, 18.6m; source qualification above still applies |
| Macro range/provenance unit tests | 0 | overnight-macro-data-tests.log: ten passed |
| Macro page old-source negative control | 1 | overnight-macro-page-before.log: all four new assertions fail on old date, quality, range and unavailable behavior |
| Corrected macro page/helper unit selection | 0 | overnight-macro-page-after.log: 14 passed, 5.13s |
| Old-build macro/GEX browser negative control | 1 | overnight-macro-options-negative-01.log/json: macro expected 28 Aug but rendered 12 Sep; GEX test incorrectly expected HTTP 200 instead of documented 201 |
| Corrected GEX negative control, unchanged old build | 1 | overnight-options-negative-02.log: -2,400,000 label begins at x=-5.98046875; trace preserved in overnight-options-negative-02-failures |
| Final Node 22 Next build | 0 | overnight-macro-options-build.log |
| Final TypeScript / ESLint | 0 each | overnight-macro-options-types.log / overnight-macro-options-lint.log |
| Final complete terminal Vitest | 0 | overnight-macro-options-full-ui.log: 317 tests, 25 files, 60.34s |
| Rebuilt macro-provenance/options-layout/options-research browser selection | 0 | overnight-macro-options-positive-01.log/results.json: three passed, zero retries, 40.4s |
| Secret and broker-action scans | 0 each | overnight-macro-options-secrets.log / overnight-macro-options-no-execution.log |

Macro panels use observation dates, actual contributing sources/quality and
unavailable gaps; ingestion time is separately labelled. Calendar ranges replace
row-count approximations. MAX retains all fetched observations (request limit
10,000), not a claim of unbounded history. GEX uses chart-local containLabel sizing;
no global chart spacing, financial value, tolerance or retry was changed.

Inspected corrected screenshots: logs/macro-screenshots/provenance-{1366,390}.png
and logs/options-layout/gamma-{1366,390}.png. Negative signs are visible and the
macro dates read 28 Aug rather than ingestion day. Canvas and document bounds pass.
Additional 1920px route reviews included alpha, backtests, macro, portfolio,
data drop/catalogue, quant, hedge, Excel, Deck, stress and risk/trade. The old
portfolio-command-centre-1920.png (6e707d3, SGD70K) is stale and excluded from
current evidence. Full visual matrix and 27-gate release remain open.

## Macro API Contracts

2026-09-12 07:15-07:22 SGT, 804ec29 plus macro API worktree. Observation-level
provider now accompanies the displayed value rather than series metadata.
History limits are 1..10,000 at HTTP and service boundaries. Return contracts
document nullable decimal strings, calendar dates and separate ingestion times.

| Command / check | Exit | Evidence |
| --- | --- | --- |
| New macro regression negative control | 1 | overnight-macro-contracts-negative.log: five failed, seven passed; four product defects (provider and three limits), plus incorrect new-test zero spelling (0.00000000 instead of existing Decimal str 0E-8) |
| Corrected contract tests | 0 | overnight-macro-contracts-positive.log: 15 passed, three warnings, 6.34s; zero spelling matches the existing wire contract, not changed arithmetic |
| Macro/provider/FRED/report/API affected selection | 0 | overnight-macro-affected.log: 110 passed, three warnings, 25.84s |
| Final macro/report consumer selection | 0 | overnight-macro-final-consumers.log: 18 passed, three warnings, 6.92s |
| Read-only prior/current response comparison | 0 | overnight-macro-parity.log: 73 complete responses equal 804ec29 on an in-memory copy of populated SQLite data; source database untouched |
| Focused strict contracts/new tests | 0 | overnight-macro-focused-types.log: two files, imported dependencies silent only in this focused command |
| OpenAPI generation and contract assertions | 0 | overnight-macro-openapi.log: 170 paths, 85 schemas; bounds/default and nullable string values verified |
| Whole strict 25 | 1 | overnight-whole-types-25/: 1,254 distinct diagnostics, 94 files, 276 sources; API 623 in 27 files |
| Whole strict 26 | 1 | overnight-whole-types-26/: API 622 after workbook consumer correction; formatter ran during distribution checks, so aggregate 1,260 includes mixed line locations and is not a stable count |
| Stable whole strict 27 | 1 | overnight-whole-types-27/: 1,252 distinct diagnostics, 94 files, 276 sources; API 622 in 27 files; source unchanged throughout the check |
| Changed-source Ruff | 0 | all four files pass |
| Changed-source format | 1 then 0 | long workbook row annotation required formatting; corrected, four files pass |
| Secret / no-execution scans | 0 each | overnight-macro-api-secrets.log / overnight-macro-api-no-execution.log |
| Observe-only Docker watchdog | 0 | overnight-macro-watchdog.log, 2026-09-11T23:17:25Z: ten healthy services, successful initializer, no restart actions |

The remaining whole strict check is still red. Macro vintage-selection semantics
are unchanged by this batch; revision preservation/current-vintage presentation
still requires separate certification. No live-provider or release-completion
claim is made. Docker is still cbb2cf1 until the forthcoming completed refresh.

## Typed Test Fixtures And Macro Deployment

2026-09-12 07:22-07:28 SGT, 0699ab0 plus test-only worktree. Numerical reference
values, seeds, financial tolerances, expected unavailable states and execution
guards are unchanged. Required results are explicitly checked before arithmetic;
persisted JSON/model rows are narrowed before field access. Settings use their
declared aliases with identical values, and provider transport fixtures retain
the same five adapters.

| Command / check | Exit | Evidence |
| --- | --- | --- |
| Option/risk/valuation tests | 0 | overnight-test-contracts-01.log: 35 passed, one warning, 7.35s |
| Initial focused strict for those tests | 1 | overnight-test-contracts-types-01.log: one remaining untyped HedgeService constructor; not suppressed |
| Initial provider test strict | 1 | overnight-test-contracts-types-02.log: five diagnostics, fixed with explicit JSON fixture type and declared Settings aliases |
| Final four-module affected tests | 0 | overnight-test-contracts-02.log: 83 passed, one warning, 9.44s |
| Final provider/options/risk focused strict | 0 | overnight-test-contracts-types-03.log: three modules; dependencies not certified by imports-silent check |
| Whole strict checkpoint 28 | 1 | overnight-whole-types-28/: 1,134 distinct diagnostics, 91 files, 276 sources; API 622 in 27 files |
| Affected Ruff | 0 | four test modules pass |
| Docker application image build | 0 | overnight-macro-docker-build.log: all five images built before up began |
| Detached health-gated Docker refresh | 0 | overnight-macro-docker-up.log: existing services refreshed, no volume/data resets |
| Observe-only watchdog | 0 | overnight-macro-deployed-watchdog.log, 2026-09-11T23:26:42Z: ten healthy services, init succeeded, no restart actions |
| HTTP main route | 0 | /overview returns 200 at sign-in, Keep-Alive timeout=70 |
| Container source hashes | 1 then 0 | initial incorrect /app/services/api/app path rejected; Dockerfile-confirmed /app/app hashes equal source: macro 49072777bbbd8421a847363cc1c3392928f808cf8876a8d5e2bdd64a18661672; simulation 64068e18a949d726f611133c38014278850537ddb3db986efcd36cc1f2d6dbb9 |

Browser 14 is active with 47 tests and zero retries. Runtime source is held at
0699ab0 during this invocation; frontend files equal the macro/options build.
No new complete browser/backend or final release pass is claimed at this point.

2026-09-12 07:29-07:32 SGT: the pre-push scan for ddfc83c returned 1 for the
existing public fake market key after its constructor keyword changed to the
declared uppercase alias. The command sequence incorrectly continued to push;
this was not a successful security gate and is recorded as an operator error.
The flagged value is a deterministic mock fixture, not a real credential.

The scanner now permits only that exact path/key/literal triple. Other values,
files, keys, expressions and token-shaped content remain blocking and redacted.
No file-wide or pattern-wide exemption is added. Ten scanner regressions pass
(overnight-secret-fixture-tests.log, native 0, 0.88s), strict types pass for both
modules (overnight-secret-fixture-types.log, native 0), and the rescan reports
615 text files, zero findings (overnight-secret-fixture-scan.log, native 0).
Ruff initially found one import-group spacing error; the spacing was corrected.
