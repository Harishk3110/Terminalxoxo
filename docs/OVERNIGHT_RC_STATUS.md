# Overnight Release Status

Controlling directive: final overnight continuation, 2026-09-12 SGT.
Starting commit: 3466694fd7513bf1c494419ab0fb09767748cd0e.
Branch: main. Remote: https://github.com/Harishk3110/Terminalxoxo.git.
Recovery tag: pre-overnight-rc-closure, pushed before code changes.

M1 pipeline: owned SQL report jobs, pinned input, write-once outputs, authenticated
XLSX/PPTX/PDF downloads and observed worker health/metrics are implemented. All 16
kind/format combinations produce real files in tests. Financial-model report depth
and rendered artifact review remain PARTIAL; these are source-pinned review exports.

Next milestone: M2 static cleanup, then full browser closure. First unchecked report
subtask: complete financial model/deck content and actual rendered-artifact review.
Next code batch: remaining engine/API contracts and final visual-workflow review.
Dated stress/hedge selection is implemented. Historical valuations no longer rewrite
the current portfolio projection; the calculation version is now knk-nav-4.9.
Whole first-party type command: `.venv-sprint/Scripts/python.exe scripts/check_python_types.py`.

Current evidence:
- Full backend rerun: 1,059 passed / 13 warnings / 337.36s; 10,309/11,784 statements covered.
- This run includes the type-gate and retired-service regression tests.
- Subsequent native-chart report selection: 34 passed. Eight new report/watchdog
  modules passed scoped strict mypy; changed modules passed Ruff.
- Full frontend rerun: 251 terminal + 5 shared tests passed (256 total).
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
scripts, tests, typings, infrastructure and migrations: 255 files including the
template tests. The subsequent expanded format check reports 259 formatted files.
Mypy is NOT green: API-only 1,119 errors in 37 files; whole first-party runner
reports 1,995 distinct diagnostic lines in 133 files across nine distributions.
The latest whole-run inventory contains 239 files, including the new gate tests.
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
security checks were weakened. Full browser zero-failure gate is still open.
The first browser full run had 30 passes and six failures. Dated analytical fixtures
then passed all six affected cases. The expanded 37-test full run is underway;
three assertions pinned to the old valuation version were corrected. That run
finished 34/37. The next populated-view run finished 36/37, exposing an actual
upload-to-backtest symbol handoff bug and a test that could accept an older run.
Both are corrected; the focused browser workflow now passes with a QQQ dataset
and native USD base currency, without fabricated FX. All requested pages are
included at four desktop sizes and 390px; another full run and screenshot review
are underway. No whole-browser or release-candidate pass is claimed yet.

Ten long-running Docker services, including reports, are healthy; MinIO init exited
0. Runtime currently carries df8dab6. The earlier refresh was interrupted by the old
watchdog's startup bug; diagnosis, correction and recovery passed. Images for the
dated-valuation batch are built and await refresh; the corrected watchdog is active.
Local URL: http://127.0.0.1:3001/overview (private login, not hosted).
Existing SQLite, local objects, `.env`, Compose credentials and volumes are preserved.
PostgreSQL backup/restore, all dashboards, release runner and later domain gates
remain open. No live provider or cloud deployment is certified. No execution added.
