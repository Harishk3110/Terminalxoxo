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
missing and 31 existing excluded. Full backend 35 has now started on frozen
41baacb, fresh isolated database/storage/auth paths; result pending.

The old 27-gate release result remains historical. The latest directive requires
29 ordered stages; neither that complete run nor final code completion is claimed.

## Single-Period Chart Regression In Progress

FiscalChart is exposed for direct component testing; calculation behavior was
unchanged for the negative control. Initial Vitest command failed before tests
because its relative executable path did not exist in the app workspace; the
corrected command uses C:/Dev/node_modules/vitest/vitest.mjs with Node 22.
Negative unit 02: two failed/two passed, native 1, 27.79s. Positive unit 01 after
the scoped isolated-point change: four passed, native 0, 2.92s. Receipts:
logs/final-fiscal-chart-units-{negative-01,negative-02,positive-01}.log.
Tests retain zeros, signed values, missing gaps, connected-line style and ordering.
The pending browser assertion inspects series-colored pixels inside the plot,
excluding legend/axis/toolbox; its runtime verification and production build are
not yet certified. Python source remains unchanged during backend 35.
