# Final Closure Build Evidence

Directive transition: 2026-09-12 SGT, application 41baacb, main, pushed. Earlier
complete command history is retained in OVERNIGHT_RC_BUILD_EVIDENCE.md.

## Current Source Checks

Curated financial adapter 41baacb reuses the existing hash-verified dataset reader
and adds typed matching rows/periods, finite metrics and positive scaling. Exact
Decimal conversion, zero/signed values, missing fields and partial restatements
are preserved. No provider freshness, execution or real-data claims were added.

| Command / receipt | Result |
| --- | --- |
| pytest tests/sprint/test_curated_fundamentals.py -q, before guards; logs/overnight-curated-negative-01.log | native 1: 27 failed, 9 passed, 1 warning, 5.28s |
| Focused five-file pytest; logs/overnight-curated-positive-01.log/xml | native 0: 163 passed, 3 warnings, 34.49s |
| Affected 16-file pytest; logs/overnight-curated-positive-02.log/xml | native 0: 300 passed, 3 warnings, 44.76s |
| mypy --strict --follow-imports=silent on adapter/test, focused-types-01.log | native 1: eight test-only JSON-indexing errors |
| Same focused command after explicit nested-shape assertions, focused-types-02.log | native 0: two source files |
| python logs/overnight-curated-parity.py, parity-01.log | native 0: 30 complete responses, 150 statement selections, 750 ratio maps, 1,000 numeric float bits exactly match 3156aec, including dictionary/report order |
| python scripts/check_python_types.py --output logs/overnight-whole-types-51 | native 1: 635 distinct diagnostics, 65 files, 315 sources, nine distributions; observed 2026-09-12T07:30:20.634179Z |
| corepack pnpm dlx node@22 node_modules/@playwright/test/cli.js test tests/e2e/equity-import.spec.ts tests/e2e/equity-research.spec.ts | native 0: three passed, no skips/retries/errors, 66.670761s; start 2026-09-12T07:32:42.948Z |
| Browser receipt logs/overnight-curated-browser-10-results.json and API log | zero global/test/API error, traceback, 500 or lock matches |
| Strict standalone TypeScript on tests/e2e/equity-import.spec.ts; logs/overnight-curated-browser-types.log | native 0, no skipLibCheck added |
| Whole Ruff and format over seven first-party roots | native 0 each, 336 formatted files |
| OpenAPI generation | native 0, 170 paths |
| Secret / no-execution scans before push | native 0 each; 658 text files, zero secret findings |

All Python commands above used .venv-rc (Python 3.12.13 / SQLite 3.53.1).
Application/tests stayed frozen during their invocations. Browser inputs were
fictional and isolated; no live provider or user portfolio was modified.

Six browser-10 screenshots were inspected: financial-import-1440/390,
dcf-1440/390, thesis-390 and security-m5. Inspection found a real remaining
single-period FIN plot defect: values are in the table but the line chart has
symbol:none and cannot draw a one-point line. Do not call this a visual pass.

## Runtime And Fresh Audit

Curated Docker build/up --wait both native 0. The first observe-only probe ran
during startup and correctly returned native 1: three workers STARTING and
Prometheus UPSTREAM_UNHEALTHY, no actions. After startup completed, probe 02
returned native 0 at 2026-09-12T07:36:56.883322Z: ten healthy services, init
SUCCEEDED, no actions. Both receipts retained in logs/overnight-curated-watchdog*.log.
API/workspace curated_fundamentals.py SHA256 matches:
3e35377b994852f116e594d4cc9661c3f646c044e542f76592c4f380d1f72f6c.
Private /overview HTTP 200 at sign-in, Keep-Alive timeout=70. No data reset.

After the new directive, separate Git status/branch/HEAD/log/remote calls return
native 0 at 41baacb. Only pending overnight documentation edits existed. Compose
ps --all and config --quiet return native 0; config was not printed because it
contains resolved secrets. Fresh observe-only watchdog native 0, receipt
logs/final-closure-baseline-watchdog.log. Ten services remain healthy.

Full backend 34 previously passed on 3156aec: 1,947 tests, zero failures/errors/
skips, 123 warnings, 485.02s. Coverage 11,976/13,349 = 89.71458536219941%, 1,373
missing and 31 existing excluded. Full backend 35 on frozen 41baacb Python source:
1,983 passed, zero failures/errors/skips, 123 warnings, 515.06s, native 0. XML
duration 515.041s, start 2026-09-12T21:13:51.022198+08:00. Coverage 12,034/13,407
= 89.7590810770493%, 1,373 missing, 31 excluded. Receipts:
logs/overnight-backend-35.log/xml and logs/overnight-coverage-35.json. Fresh isolated
database/storage/auth paths; only frontend and documentation edits during this run.

The old 27-gate release result remains historical. The latest directive requires
29 ordered stages; neither that complete run nor final code completion is claimed.

## Single-Period Chart Correction

FiscalChart is exposed for direct component testing; calculation behavior was
unchanged for the negative control. Initial Vitest command failed before tests
because its relative executable path did not exist in the app workspace; the
corrected command uses C:/Dev/node_modules/vitest/vitest.mjs with Node 22.
Negative unit 02: two failed/two passed, native 1, 27.79s. Positive unit 01 after
the scoped isolated-point change: four passed, native 0, 2.92s. Receipts:
logs/final-fiscal-chart-units-{negative-01,negative-02,positive-01}.log.
Tests retain zeros, signed values, missing gaps, connected-line style and ordering.
The browser assertion inspects series-colored pixels inside the plot, excluding
legend/axis/toolbox. Old-build negative 01 JSON: one failed, zero passed/skipped/
flaky, 52.822581s; both series-visible assertions false. Native process exit was
not recovered across context transition; no native result is claimed for it.
Corrected positive 01: three passed, native 0, zero failures/skips/retries/flaky/
global errors, 65.647701s, start 2026-09-12T13:27:32.120Z. Both 1440/390 plot
pixel checks pass. API/report logs have zero traceback/500/lock error matches.
All six financial-import/DCF/thesis/security screenshots reviewed. Connected DCF
lines and all underlying values/order are unchanged. This is focused visual
acceptance, not certification of the full visual suite.

Frontend full units: 337 passed / 27 files, native 0, 16.58s, JUnit retained at
logs/final-fiscal-frontend-units-01.xml. Node 22 production build native 0 at
logs/final-fiscal-build-01.log. Terminal typecheck 01 native 0; lint 02 native 0
(lint 01 exit was not retained, so rerun explicitly). Browser strict TypeScript
native 0 in logs/final-fiscal-browser-types-01.log. Runtime Node for build/tests:
22.23.2; pnpm terminal typecheck/lint used the host Node 20 launcher and warned
about the app engine, without a type/lint failure. Test formatting only was
normalized after the completed browser run; application code remained unchanged.

## Required 29-Stage Runner

Broker-action scan moved to stage 3; migration upgrade and downgrade/upgrade
split into stages 5/6 with separate isolated paths/JUnit. Frontend and shared
units split into stages 15/16 using Node 22 Vitest and clean nonempty JUnit
receipts. Shared tests discover packages, not echo-only package scripts. Remaining
order matches the latest directive. No old safeguard or critical command removed;
coverage remains 86.58%, source changes fail, browser retries remain zero.

Negative ordered-contract tests: four failed, 31 deselected, one warning, 1.32s,
native 1 (logs/final-release-order-negative-01.log). Corrected runner/result tests:
55 passed, zero skips, one warning, 12.31s, native 0; log/XML positive-01. Focused
strict mypy on runner/checks/test: three files, native 0. Whole Ruff/format native
0 each, 336 files formatted. Existing five shared tests pass / two files, native
0, 2.47s, logs/final-release-shared-units-01.log/xml. Migration upgrade: 17 passed,
one deliberately deselected roundtrip (executed separately), one warning, 17.58s,
native 0. SQLite/PostgreSQL roundtrip: two passed, one warning, 15.42s, native 0.
Receipts logs/final-release-migration-{upgrade,roundtrip}-01.log/xml. PostgreSQL
uses a newly allocated isolated database; the active book is untouched. All five
new XML receipts pass the real release_results validator with native 0.

Whole strict run 52: native 1, unchanged 635 distinct diagnostics / 65 files /
315 sources / nine distributions. API 323 / 13 / 122. Observed
2026-09-12T13:32:09.889259+00:00, logs/final-release-whole-types-52/manifest.json.
No diagnostics in modified runner/checks/test files. These focused commands do
not claim that the complete 29-gate release has passed.
