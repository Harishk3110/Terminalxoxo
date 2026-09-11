# Overnight Release Status

Controlling directive: final overnight continuation, 2026-09-12 SGT.
Starting commit: 3466694fd7513bf1c494419ab0fb09767748cd0e.
Branch: main. Remote: https://github.com/Harishk3110/Terminalxoxo.git.
Current HEAD: 6edb4e2, pushed. Dated-source/options/risk, ledger/factor, local
archive/reader, ASGI concurrency and bounded agent status fixes are committed.
Local backup manifest and recovery probe/migration contracts are also committed.
Factor request/loading improvements are committed and deployed locally. Typed alpha
statistics and the verified regression-library boundary pass focused checks.
Full release remains open.
Recovery tag: pre-overnight-rc-closure, pushed before code changes.

M1 pipeline: owned SQL report jobs, pinned input, write-once outputs, authenticated
XLSX/PPTX/PDF downloads and observed worker health/metrics are implemented. All 16
kind/format combinations produce real files in tests. Native DCF/WACC/forecast/
sensitivity formulas now reconcile to pinned inputs and independent Excel
recalculation. Remaining financial-model/deck depth is PARTIAL.

Next milestone: M2 static cleanup and source precedence, then full browser closure. First unchecked report
subtask: complete financial model/deck content and actual rendered-artifact review.
Verified agent batch: durable local archive journal, validated acknowledgements,
typed reader contracts, nonzero broker client IDs and explicit derivative
multiplier availability. Existing queue records are preserved. Current code batch:
keep blocking database access out of asynchronous middleware and reconcile older
agent uploads using bounded identity lookups with ownership/hash verification.
Next batch: remaining engine/API contracts and source-adapter completeness.
Dated stress/hedge selection is implemented. Historical valuations no longer rewrite
the current portfolio projection; the calculation version is now knk-nav-4.9.
Whole first-party type command: `.venv-sprint/Scripts/python.exe scripts/check_python_types.py`.

Current evidence:
- Full backend 22: 1,300 passed, 13 warnings, 427.31s; coverage remains
  10,901/12,366 statements (88.1530%). This precedes the typed-alpha batch.
- Typed alpha selection: 20 passed. Nine complete and four unavailable results
  match 6edb4e2 exactly. Four independent Bartlett HAC/t-inference checks pass.
  Whole strict checkpoint 17: 1,535 diagnostics / 102 files / 270 sources;
  API is 877 diagnostics. The alpha statistics source and its tests pass strict types.
- Factor projection has exact old/new equality for 54,241 observations and 18
  complete factor results. Affected backend selection: 42 passed. Terminal unit
  suite: 270 passed. Node 22 build, TypeScript and ESLint pass. Rebuilt operating/
  quant browser selection: four passed; deliberate overlap/reload test: one passed,
  both with zero retries and no recorded database-lock or HTTP 500 failures.
  Full browser 11 (40 tests) remains active; its two quant journeys have passed.
- Recovery/backup focused selection: 45 passed. Migration selection: 19 passed,
  including real isolated PostgreSQL lifecycle and three URL configuration tests.
  Whole strict checkpoint 16: 1,564 diagnostics / 104 files / 267 sources. No
  diagnostics originate in repository-tools, though imported API errors keep that
  distribution's invocation red. API still has 901 diagnostics in 33 files.
- Current focused selection: 71 passed, three warnings, 32.65s. Full backend 21:
  1,263 passed, 13 warnings, 447.63s; 10,901/12,366 statements covered (88.1530%).
  Browser 10 finished: 37 passed / two failed / zero retries, 23.0m. All five
  viewport sweeps passed. Both failures are in quant; traces are preserved under
  logs/overnight-full-10-failures. Backend 22 has passed as recorded above.
- Local backup manifest selection: 23 passed, native exit 0; six affected source
  and test files pass strict types. Malformed and duplicate manifest fields are
  rejected before creating the restore target. This is separate from backend 21.
- Browser 09: 38 passed / one failed / zero retries, 20.7m. All five viewport
  sweeps passed; quant hit SQLite lock errors. The new ASGI checks pass two
  deterministic concurrency regressions but have not closed the database locks.
- Agent/reader focused selection: 30 passed; both source modules and both new test
  modules pass strict types. Ruff/format/pip check pass. Full backend run 19:
  1,244 passed, 13 warnings, 447.09s; 10,875/12,341 statements covered (88.1209%).
  Whole type checkpoint 13 still fails; local-agent has no diagnostics.
- Docker image build and health-gated refresh for 364503e passed. The full browser
  run 09 finished with the quant lock failure described above. The ASGI fix is
  not yet deployed to the persistent Docker stack.
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
scripts, tests, typings, infrastructure and migrations: 285 formatted files.
Mypy is NOT green: checkpoint 14 has 901 API errors in 33 files; the whole runner
reports 1,608 distinct diagnostic lines in 117 files across nine distributions.
Checkpoint 13 had 1,619 diagnostics. The source-only checkpoint 09 had 1,859.
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
a3a5d79 and now the ledger/factor fix from 364503e. API/worker/report/UI
builds and refresh passed. A subsequent build and health-gated refresh deployed
6edb4e2 to API, data/quant workers, reports and terminal. All ten services and the
MinIO initializer pass the observe-only watchdog. The later alpha typing changes
are not part of that Docker image. The
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
Exact next command: `Get-Content logs/overnight-browser-full-11.log -Tail 8`.
Complete full browser 11 and continue engine/API contracts. Align and verify the
scientific dependency stacks: Windows currently uses NumPy 2.2.1/SciPy 1.14.1;
Docker uses NumPy 2.5.3/SciPy 1.18.1. Both use statsmodels 0.15.0. No cross-runtime
numerical equivalence or dependency alignment is claimed yet.
Agent startup installation, structured
logs and separate file/broker credential profiles remain open. A separate review
move journal is still needed for a hard interruption between its rename and
queue commit; the completed archive journal does not cover that earlier move.
