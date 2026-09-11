# Overnight Release Status

Controlling directive: final overnight continuation, 2026-09-12 SGT.
Starting commit: 3466694fd7513bf1c494419ab0fb09767748cd0e.
Branch: main. Remote: https://github.com/Harishk3110/Terminalxoxo.git.
Current HEAD at verification: a3a5d79, pushed. Dated-source, typed-options, risk
empty-state, ledger refresh and factor performance changes are verified for this
batch and ready to push. Full release acceptance remains open.
Recovery tag: pre-overnight-rc-closure, pushed before code changes.

M1 pipeline: owned SQL report jobs, pinned input, write-once outputs, authenticated
XLSX/PPTX/PDF downloads and observed worker health/metrics are implemented. All 16
kind/format combinations produce real files in tests. Native DCF/WACC/forecast/
sensitivity formulas now reconcile to pinned inputs and independent Excel
recalculation. Remaining financial-model/deck depth is PARTIAL.

Next milestone: M2 static cleanup and source precedence, then full browser closure. First unchecked report
subtask: complete financial model/deck content and actual rendered-artifact review.
Current code batch: dated market/FX source selection, typed history and options
results, historical option-contract identity, explicit risk empty states,
initial-read cancellation after ledger writes and shared/vectorized factor reads.
Next batch: remaining engine/API contracts and source-adapter completeness.
Dated stress/hedge selection is implemented. Historical valuations no longer rewrite
the current portfolio projection; the calculation version is now knk-nav-4.9.
Whole first-party type command: `.venv-sprint/Scripts/python.exe scripts/check_python_types.py`.

Current evidence:
- Full backend run 18: 1,214 passed, 13 warnings, 469.49s; 10,871/12,341
  statements covered. This includes the final factor read/calculation changes.
- FX/market/history/research/type-runner selection: 46 passed. Options selection:
  37 passed. A separate baseline comparison passes all 144 chain and 144 position
  cases with exact result equality, not relaxed tolerances.
- Frontend: 266 terminal + five shared tests passed (271 total), including five
  risk empty-state tests and five pending-initial-read ledger regressions. Current
  TypeScript, lint and the final ledger-refresh Node 22 production build pass.
- Risk unavailable browser tests: two passed, zero retries; desktop/mobile
  screenshots inspected. Docker UI/API/worker/report refresh returned healthy.
- Full browser run 08: 36 passed / three failed / zero retries, 23.3m:
  ledger initial-read refresh race, factor short-history fixture assumption, and
  factor request latency under repeated controls. The fresh-build three-journey
  rerun passed, native exit 0, zero retries, 2.7m. No full-browser pass is claimed
  for this final version yet.
- Factor shared-read regression: two failed before fix; 29 affected tests passed
  after. Optimized-factor selection: 22 passed. Direct pandas comparisons and
  18 full old/new diagnostic cases preserve exact values, including missing/tied
  observations, all six factor types and insufficient histories.
- Latest completed full backend rerun 14: 1,165 passed / 13 warnings / 300.50s;
  10,598/12,078 statements covered (87.7463%), including native DCF and runner tests.
- Runner/result/seed selection: 54 passed; six runner/result/lifecycle modules
  pass scoped strict types. The whole type gate still fails.
- Real PostgreSQL migration and API/report-worker restart: two passed, 72.60s.
  Buy/partial sale/dividend, saved NAV, session and private report hash survive
  distinct process restarts. Fresh-seed daily lookups were removed without
  changing history or relaxing the 120-second startup deadline.
- Actual PowerShell release checkpoint 20260911T193027Z-5985dadc passed gates 1-6,
  including 16 SQLite/PostgreSQL migration tests with no skips; gate 7 failed.
  Gates 8-27 were NOT_RUN in this invocation. No all-gates release pass is claimed.
- Windows Excel integration: three passed, 88.78s in final run 02; 1,085 formulas
  recalculated, plus changed-revenue and invalid-perpetuity checks. Local rendered
  one-/ten-year workbooks were inspected; other report-family artifacts remain open.
- Subsequent native-chart report selection: 34 passed. Eight new report/watchdog
  modules passed scoped strict mypy; changed modules passed Ruff.
- Full frontend rerun: 256 terminal + 5 shared tests passed (261 total), including
  compact chart-axis and percentage-label regression tests.
- Workspace TypeScript/lint and Node 22 local/Docker production builds passed.
- Report browser workflow passed twice, including the mobile resize fix and
  persisted date/format; screenshots at 1440px/390px were inspected.
- Isolated PostgreSQL/MinIO report smoke passed: three formats, hashes, owned
  download, anonymous rejection and persistence after worker termination.
- Seven migrations: SQLite lifecycle and PostgreSQL fresh/latest roundtrip passed.
- Watchdog: six tests and live observe-only pass; replacement hidden launcher
  PID 24200 is active. Normal Docker startup no longer triggers a restart, and
  upstream scrape failures do not restart healthy Prometheus.

First-party Ruff passes. The latest format command includes services, packages,
scripts, tests, typings, infrastructure and migrations: 276 formatted files.
Mypy is NOT green: checkpoint 12 has 913 API errors in 33 files; the whole runner
reports 1,667 distinct diagnostic lines in 119 files across nine distributions,
with 260 inventoried files. Checkpoint 11 had 1,732 diagnostics; factor result
contracts removed another 65. The source-only checkpoint 09 had 1,859 diagnostics.
The runner
now pins PYTHONHASHSEED to keep diagnostic ordering stable. Pandas 2.2.3 stubs were
updated to their compatible May 2025 revision; runtime pandas was not changed.
The engine, native builder, renderer, consumers and runner pass their scoped type
checks. Remaining engine/API/imported test diagnostics have not been hidden.
Flat invocation previously stopped on duplicate app/agent names; distribution
grouping and explicit namespace bases for repository tools/tests fix that problem
without suppressing errors. The runner and its tests pass strict mypy.
Model/repository/price-source contracts and eight consumer/watchdog modules pass
scoped strict checks; local
vollib signatures pass runtime stub verification. No global ignores were added.
Provider/storage/option/report follow-up: 82 focused tests passed. OpenAPI generated
170 paths and 73 component schemas after adding typed provider responses.
The first M2 full run had 14 fixture registration errors after lint autofix;
explicit fixture re-exports fixed them. The 17-test affected selection and the
subsequent complete 973-test run passed without disabling any lint or test checks.
The first full backend attempt used incompatible test/HTTPS-cookie configuration:
949 passed / 3 failed. Correct local-demo auth selection passed all 47; no runtime
security checks were weakened. Full browser run 04 passed 37/37 with zero retries.
Run 05 added selected file/dataset views and failed four duplicate-draft fixtures.
Viewport-specific unapproved drafts fixed fixture isolation; both targeted sizes
then passed. Full run 06 passed 37/37, zero retries, 8.9m. Uploaded backtesting
still asserts the newly queued QQQ run and native USD without fabricated FX.
Visual review subsequently found crowded NAV/percentage ticks and risk-monitor
grid tracks extending beyond their parent rows at 1366px. The new containment
assertion failed against the old build; the corrected build passed both targeted
1366px/390px visual journeys (2.2m). Updated overview/performance/risk-monitor/risk
screenshots at 1366px were inspected: labels and panel containment are corrected.
Full browser run 07 passed all 37 tests, zero retries, 8.3m. Its JSON receipt is
preserved in logs/overnight-full-07-results.json. Additional 2560px overview,
performance and risk-monitor screenshots were inspected. Complete visual and
release-candidate acceptance are not claimed.

Ten long-running Docker services, including reports, are healthy; MinIO init exited
0. Runtime carries the dated-source/options/risk-availability batch based on
a3a5d79. The newer ledger/factor fix is not yet deployed. API/worker/report/UI
builds and refresh passed. The
earlier frontend refresh returned healthy, but the PowerShell command wrapper
reported exit 1 on Docker stderr progress. An explicit native-exit-code verification
with --no-deps returned 0; the corrected watchdog remains active.
Local URL: http://127.0.0.1:3001/overview (private login, not hosted).
Existing SQLite, local objects, `.env`, Compose credentials and volumes are preserved.
PostgreSQL backup/verification/private isolated restore pass for 113 tables and
four non-probe objects, with all table/content hashes reconciled. The three
ephemeral readiness probe names are explicitly excluded in the manifest. A real
concurrent-write integration test passes. Backup metrics, read-only receipt mount
and Prometheus alert rules are live; offsite retention and external alert delivery
require operator configuration. See MANAGED_BACKUP.md and build evidence.
Ten dashboards, full release-runner acceptance and later domain gates remain open. No live provider
or cloud deployment is certified. No execution added.

Focused equity/report browser rerun: three passed, zero retries, 1.2m.
Additional direct review: mobile macro/options/risk screenshots fit their viewports;
risk's unavailable chart panels now have verified empty-state treatment. Other
unreviewed desktop combinations remain open.
Additional direct review: overview, risk and options screenshots at 1920px were
inspected. Risk's all-null panels prompted the empty-state fix verified in two
new browser tests; the remaining viewport matrix is not certified complete.
Exact next command: `docker compose --env-file .env.compose.local -p knk-final-local build terminal-web api worker-data worker-quant report-engine`.
After refreshing the images: full browser rerun, then remaining engine/API and
local-agent contracts. The local-agent archive acknowledgement crash path is open.
