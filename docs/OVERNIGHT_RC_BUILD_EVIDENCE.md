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
| Full browser run 07 | Running; no full-pass claim for this revision yet | overnight-browser-full-07.log |

The initial chart test needed the jsdom environment and an explicit value-axis
type guard. Both were corrected without suppressing TypeScript diagnostics.
Direct review of the corrected 1366px overview, performance, risk-monitor and
risk screenshots confirms the label/containment changes. Screenshots are local
evidence only; no all-pages/all-sizes visual-completion claim is made.
