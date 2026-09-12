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

## Chart Deployment 9a85cbe

Commit/push native 0 to main. Pre-push scans: 667 text files, zero secret findings;
broker-action scan native 0. Terminal Docker build/up --no-deps --no-build --wait
native 0 each (logs/final-fiscal-docker-{build,up}-01.log). Watchdog native 0 at
2026-09-12T13:38:32.928522+00:00: ten healthy services, init SUCCEEDED, no actions.
HTTP /overview 200, private sign-in, Keep-Alive timeout=70. Build ID
NhNZtzzxvdumdoktPDmTC; equity-page.tsx workspace/container SHA256:
0486e92cedd50e8a12b8b6031521e3f3c48e45e881e3e9eb7c5f127e05ee3cf4.
API/worker/report images remain 41baacb during this frontend-only deployment.

## Reconciliation Financial Boundary

Preserved the existing comparison arithmetic/tolerances and break state lifecycle.
Typed header/book/snapshot/fill inputs use the existing accounting decimal guard
and ordered financial-source validator. Unknown source fill fields and order are
retained. Missing internal NAV no longer places a raw Decimal inside the SQL JSON
break payload: existing jsonable converts it exactly to a string. Either observed
side is validated even if its counterpart is missing. Invalid saved inputs return
generic HTTP 422 without financial values. Valid unconnected headers do not require
cash/position/transaction comparisons or apply comparison limits.

All commands use .venv-rc Python 3.12.13 unless stated. Native results retained:

| Receipt under logs/ | Result |
| --- | --- |
| final-reconciliation-negative-01.log, old service | 15 failed, two preservation cases passed, one warning, 4.42s, native 1; includes real Decimal JSON failure |
| final-reconciliation-positive-01.log/xml | 60 passed, three warnings, 16.25s, native 0 |
| final-reconciliation-focused-types-01.log | two strict files pass, native 0 |
| final-reconciliation-operations-types-01.log | native 1, 14 errors: 13 pre-existing plus optional matched-break variable; corrected with distinct matched binding |
| final-reconciliation-api-negative-01.log | one failed, 19 deselected, one warning, 2.47s, native 1: invalid recorded value gave 500 instead of generic 422 |
| final-reconciliation-positive-02.log/xml | invocation error, native 4: nonexistent test_portfolio_commands.py; no tests certified |
| final-reconciliation-positive-03.log/xml | one failed, 140 passed, three warnings, 25.65s, native 1: new unpriced fixture omitted required instrument country; fixed fixture, not schema |
| final-reconciliation-unpriced-01.log/xml | one passed, 19 deselected, one warning, 1.64s, native 0; real ledger replay keeps missing NAV and persists warning |
| final-reconciliation-positive-04.log/xml | 141 passed, three warnings, 22.85s, native 0 |
| final-reconciliation-focused-types-02.log | two strict files pass, native 0 |
| final-reconciliation-unconnected-negative-01.log | four failed, 20 deselected, one warning, 2.09s, native 1; caught draft regression requiring comparison fields before checking whether a broker exists |
| final-reconciliation-positive-05.log/xml | final eight-file suite: 145 passed, three warnings, 24.67s, native 0 |
| final-reconciliation-security-01.log/xml | 48 passed, three warnings, 22.61s, native 0 |
| final-reconciliation-openapi-01.log | 170 paths; reconciliation response documented; native 0 |
| final-reconciliation-browser-types-01.log | strict new browser-test TypeScript, native 0 |
| final-reconciliation-ruff-02.log / format-02.log | whole first-party trees native 0 each, 338 formatted files |
| final-reconciliation-secrets-01.log / no-execution-01.log | native 0 each; 670 text files, zero secret findings; no broker actions |

New 24 regression cases cover missing-NAV warning persistence/identity/resolution,
malformed saved structures, bad numeric values with missing counterparts, zero,
signed values, existing tolerances, original fill fields/order, real unpriced
ledger replay, public error redaction, and unconnected-header compatibility.

Strict run 53 native 1: 614 distinct diagnostics, 65 files, 317 sources, nine
distributions; observed 2026-09-12T13:44:13.303720+00:00. API 310 / 13 / 123.
Final header correction run 54 native 1: 615 distinct strings, representing the
same 614 errors. services.py:1430's existing PriceProvenance missing-key error has
two different key orders across distributions. Sorting only that unordered list
gives 614; no diagnostic was discarded. Run 52 similarly gives 635 both raw and
canonical. Net reduction 21; no new semantic errors. Run 54 observed
2026-09-12T13:48:31.753792+00:00. Full logs/manifests preserved.

Browser 01: Node 22 Playwright reconciliation + operating suites, three passed,
native 0, 101.600657s, start 2026-09-12T13:44:35.169Z. Final header correction
browser 02: one passed, native 0, 25.895619s, start 2026-09-12T13:47:51.004Z.
Neither run has skipped/flaky/retried/global errors; API logs contain zero
traceback/500/lock matches. All 14 first-run screenshots inspected (five overview
sizes, seven operating desks, two reconciliation views), then both final 1440/390
reconciliation screenshots inspected. No shell redesign or frontend code change.
These are focused workflow/visual checks, not a full current browser release.

Full backend 36 completed on frozen 7703110 with fresh isolated database/storage/
auth paths: 2,009 passed, zero failures/errors/skips, 123 warnings, 511.25s.
XML duration 511.238s, start 2026-09-12T21:52:24.441723+08:00. Coverage:
12,115/13,493 = 89.78729711702364%, 1,378 missing and 31 excluded. Receipts:
logs/final-backend-36.log/xml and logs/final-coverage-36.json. The final terminal
collection output was truncated across context transition; the process session
is closed and its native exit was not recovered. No native result is claimed.
Command: .venv-rc/Scripts/python.exe -m pytest tests/sprint services/api/tests -q
--cov=services/api/app --cov-report=json:logs/final-coverage-36.json
--junitxml=logs/final-backend-36.xml. Only documentation changes and Docker deployment
occurred during this run; Python application/tests stayed frozen until completion.

## Reconciliation Deployment 7703110

Commit/push native 0. Secret scan 02 after documentation: 670 text files, zero
findings. API/data worker/quant worker/report engine build and up --no-deps
--no-build --wait both native 0, logs/final-reconciliation-docker-{build,up}-01.log.
Before/after read-only fingerprints of ten business tables match exactly, both
row counts and content hashes. Tables: portfolio_transactions, transaction_details,
transaction_revisions, portfolio_profiles, portfolio_balance_adjustments,
dataset_versions, research_notes, investment_theses, thesis_sources,
thesis_attachments. No private rows printed; only counts and hashes retained in
logs/final-reconciliation-persistence-{before,after}-01.json. Runtime heartbeat/
audit tables were not claimed unchanged. Comparison command native 0.

Post-deployment watchdog native 0 at 2026-09-12T13:57:14.332580+00:00: ten healthy
services, MinIO init SUCCEEDED, no actions. /overview HTTP 200 at private sign-in,
Keep-Alive timeout=70. Workspace/container SHA256 matches:
- portfolio_operations.py: 6a51cda301f219ee79aaeef76a71c2606b484aff45d9daf42466ace799adb163.
- reconciliation_contracts.py: 2e7a19ee96bbedc1a56ae602a75432b463289e117a471d75226219575a0673fc.
Frontend remains 9a85cbe. No hosted URL, real broker or live-provider claim.

## Trade-Monitor Evidence Boundary

Typed recorded transactions, risk snapshots, breaches, event metadata and output
rows preserve observed scalar kinds and source extension order. Missing NAV stays
missing; an observed zero/negative value is not replaced. Metadata cannot override
review state, current marks/provenance, risk results or ledger financial fields.
Legacy duplicated context fields use the effective ledger, including its symbol.
Events require a matching effective transaction in their own portfolio. Invalid
recorded inputs on GET /trades return a generic 422 without input values.
Review receipts and both route schemas are typed. The tabular workbook boundary
validates its dynamic sheet rows without changing headers, cells or formula safety.

Receipts under logs/, Python commands use .venv-rc:

| Receipt | Result |
| --- | --- |
| final-trade-monitor-negative-01.log | old service: 23 failed, four passed, one warning, 5.79s, native 1 |
| final-trade-monitor-positive-01.log/xml | 46 passed, three warnings, 15.96s, native 0 |
| final-trade-monitor-context-negative-01.log | five failed, 27 deselected, one warning, 3.40s, native 1; legacy context still overrode ledger and missing linked transaction was accepted |
| final-trade-monitor-positive-02.log/xml | 122 passed, three warnings, 24.40s, native 0 |
| final-trade-monitor-positive-03.log/xml | 186 passed, three warnings, 43.51s, native 0; includes auth, manual-only and report-source contracts |
| final-trade-monitor-focused-types-01.log | native 1: two missing adapter generic annotations; corrected |
| final-trade-monitor-focused-types-02.log | two strict files pass, native 0 |
| final-trade-monitor-operations-types-01/02/03.log | native 1 each: 19, 25, 15 errors respectively; draft workbook inference fixed with validated dynamic sheet rows; remaining 15 pre-existing ledger/API errors |
| final-trade-monitor-parity-01.log | native 0: three full fictional trade rows exactly match 7703110, including scalar kinds, values and JSON order |
| final-trade-monitor-ruff-01.log / format-01.log | native 0 each; 340 formatted files |
| final-trade-monitor-openapi-01.log | native 0, 170 paths; trade list/review responses documented |
| final-trade-monitor-browser-types-01/02/03.log | native 0 each, strict standalone TypeScript |
| final-trade-monitor-secrets-01.log / no-execution-01.log | native 0 each; 673 text files, zero secret findings and no broker actions |

Whole strict run 55: native 1, 597 distinct strings including new nullable-test
and workbook-inference diagnostics. These were corrected, not suppressed. Run 56:
native 1, 590 raw/canonical diagnostics, 65 files, 319 sources, nine distributions.
API: 292 errors / 13 files / 124 sources. Observed 2026-09-12T14:15:35.875679+00:00.
Net reduction 24 from run 54's 614 canonical errors; no new semantic errors.

Browser 01: native 1, two existing operating workflows passed; new test failed
because it filtered on a reference not exposed as a table column. JSON: two
expected, one unexpected, zero skipped/flaky/global errors; 116.409871s,
start 2026-09-12T14:15:48.946Z. All 12 operating screenshots and the failure
screenshot reviewed. Browser 02: native 1, one failed, 143.021239s, start
2026-09-12T14:18:45.978Z. The exact-label selector did not match the existing
wrapped select; screenshot confirms the trade and review form rendered. Fixed
the selector to the existing non-exact label pattern, not the application.
Browser 03: native 0, one passed, 36.754111s, start 2026-09-12T14:22:02.439Z.
Zero skipped/flaky/retried/global errors. Both 1440/390 review screenshots
inspected: saved FLAGGED state, unchanged price and ledger references. All three
API logs have zero traceback/500/lock error matches. Thirty-two new backend cases.
These are focused workflow checks; the entire browser release has not been rerun.
No frontend application or design changes. In-app connection attempt failed;
the repository's existing isolated Chromium runner supplied these receipts.

## Trade-Monitor Deployment a57bd47

Commit/push native 0; secret scan 02 native 0, 673 text files, zero findings.
Docker build and up --no-deps --no-build --wait native 0 each, receipts
logs/final-trade-monitor-docker-{build,up}-01.log. The first observe-only probe
ran during startup and correctly returned native 1, with both workers STARTING
and no actions. After up --wait completed, probe 02 returned native 0 at
2026-09-12T14:25:23.641270+00:00: ten healthy services, MinIO init SUCCEEDED.
Main /overview HTTP 200 at private sign-in, Keep-Alive timeout=70.

Read-only pre/post fingerprints match exactly for all 13 checked business tables:
the previous ten plus trade_events, trade_reviews and trade_risk_snapshots.
Both snapshot commands and their comparison returned native 0. Receipts:
logs/final-trade-monitor-persistence-{before,after}-01.json. No private rows or
connection settings printed; no volumes or user records reset. Workspace/container
SHA256 matches:
- portfolio_operations.py: 3f8886d09f2b19c7a4f1e2c789e04bc66fa9a31c1dc740b87bbb3e3133cd0113.
- trade_monitor_contracts.py: a2d5d30ab0053772204273212e50ecadf3f58d0653bcf6b5cffa860e94881182.
- portfolio_api.py: 1d46c251ba357e024f096af9b516421554c17f00316cef3f4dbf747d2534a7f7.
Frontend remains 9a85cbe. No hosted, live-provider or live-broker certification.

## Trade Recording Boundary

New invalid rationale previously persisted and could then prevent monitor reads.
Both notes and rationale now validate before inserts, including false/zero/empty
containers rather than silently replacing them. Valid null/empty-string fallback
is preserved. The typed risk snapshot factory retains all five exposure groups,
all source extensions/order, exact numeric strings and explicit missing values.
Missing calculated weight is required, not supplied as a default. JSON request
metadata and a correctly narrowed optional FX result close four more static errors.

Receipts under logs/, .venv-rc unless specified:

| Receipt | Result |
| --- | --- |
| final-trade-recording-negative-01.log | native 1: nine failed, one warning, 3.46s; three new preservation assertions had an incorrect guessed decimal scale |
| final-trade-recording-negative-02.log | native 1: six failed, three passed, one warning, 3.32s after correcting expected scale to observed original output |
| final-trade-recording-positive-01.log/xml | native 0: 131 passed, three warnings, 26.99s |
| final-trade-recording-weight-negative-01.log | native 1: one failed, nine deselected, one warning, 1.60s; draft accepted a missing weight field |
| final-trade-recording-positive-02.log/xml | native 0: 132 passed, three warnings, 25.08s after requiring the field while retaining explicit null |
| final-trade-recording-positive-03.log/xml | native 0: 182 passed, three warnings, 44.12s; includes auth/security and successful API use after rejected invalid input |
| final-trade-recording-focused-types-01.log | native 1: missing generic annotation for TRADE_TEXT; corrected |
| final-trade-recording-focused-types-02.log | native 0: three strict files |
| final-trade-recording-focused-types-03.log | native 0: three strict files, including the final twelve recording cases |
| final-trade-recording-operations-types-01.log | native 1: eleven existing errors, including two untyped calculate calls; no new errors |
| final-trade-recording-parity-01.log | native 0: three full valid trade rows exactly match 7703110 values/scalar kinds/JSON order |
| final-trade-recording-ruff-01.log / format-01.log | native 0 each, 341 formatted files |
| final-trade-recording-openapi-01.log | native 0, 170 paths; ledger metadata is a JSON object |
| final-trade-recording-secrets-01.log / no-execution-01.log | native 0 each, 674 text files, zero secret findings, no broker actions |

Whole strict 57: native 1, 586 raw/canonical errors, 65 files, 320 sources, nine
distributions; API 288 / 13 files / 124 sources. Observed
2026-09-12T14:34:58.102717+00:00. Four fewer errors than run 56, no new diagnostics.
Browser 01 (Node 22): native 0, one passed, zero skipped/flaky/global errors,
56.156265s; start 2026-09-12T14:36:08.076Z. Both 1440/390 review screenshots
inspected again. API log has zero traceback/500/lock matches. No frontend changes.
Twelve new recording cases; full current backend and deployment are pending.

## Trade Recording Checkpoint fcaa774

Commit and push returned native 0. Final secret scan 02 returned native 0,
674 text files, zero findings; diff check native 0. Focused strict 03 returned
native 0 on three files, including the final twelve recording cases.
Full backend 37 started on frozen fcaa774 Python application/tests using
isolated database, object storage and auth paths. Native exit will also be
persisted in logs/final-backend-37.exit; no result is claimed while it runs.

Observe-only runtime probe returned native 0 at
2026-09-12T14:44:20.127688+00:00: ten healthy services, MinIO init SUCCEEDED,
no actions. Receipt: logs/final-trade-recording-watchdog-01.log. Main /overview
HTTP 200 at private sign-in, Keep-Alive timeout=70. Running backend remains
a57bd47 and frontend 9a85cbe; fcaa774 deployment is pending.

## Full Backend 37

Frozen fcaa774 Python application/tests, isolated logs/final-backend-37.db,
logs/final-backend-37-objects and separate auth key, external providers disabled.
Command: `.venv-rc/Scripts/python.exe -m pytest tests/sprint services/api/tests -q
--cov=services/api/app --cov-report=json:logs/final-coverage-37.json
--junitxml=logs/final-backend-37.xml`. Native exit 0, also retained in
logs/final-backend-37.exit. XML: 2,053 tests, zero failures/errors/skips,
520.476s; start 2026-09-12T22:42:03.484534+08:00. Log: 2,053 passed,
123 warnings, 520.52s. Coverage: 12,267/13,644 = 89.90765171503958%,
1,377 missing, 31 excluded. Only documentation changed during the run.
An early receipt read failed because the process was still running; the final
native exit, XML and coverage were subsequently collected successfully.

## Trade Recording Deployment fcaa774

Docker build and up --no-deps --no-build --wait returned native 0 each, with
logs/final-trade-recording-docker-{build,up}-01.log and .exit receipts.
Observe-only probe 02 native 0 at 2026-09-12T14:55:04.712246+00:00: ten healthy
services, MinIO init SUCCEEDED, no actions. Main /overview HTTP 200 at private
sign-in, Keep-Alive timeout=70. Frontend remains 9a85cbe.

Pre/post read-only fingerprints and comparison returned native 0: all 13 checked
business-table counts/hashes are identical. Receipts:
logs/final-trade-recording-persistence-{before,after}-01.json. No private rows,
connection settings or volumes were exposed or reset. Workspace/container hashes:
- portfolio_operations.py: ac833c297282533d6d8fe7844dcad2a331191be00cb2050d71232f81b77c1293.
- trade_monitor_contracts.py: 9dd5a8abd41c53ae83f0ba4995dc6c89b83a86e2ae4d029579dbdfb10dcf9b0c.
- portfolio_api.py: 33b2df48234e3ede8d23b2c10c0d92a394a351fcf40131777d0cca4d387a381a.
No hosted or real-provider certification is claimed.

## Valuation Records

Raw position/P&L/cash/daily-curve TypedDicts retain exact amounts and missing
states. Named optional accumulators and narrowed FX/source stamps replace
ambiguous unions. Explicit position fields preserve the existing output order.
Transaction posting totals cannot be subtracted when unavailable; the new
ValueError occurs before a successful valuation run is inserted.

Receipts under logs/, .venv-rc unless stated:

| Receipt | Result |
| --- | --- |
| final-valuation-records-types-01.log | native 1: 13 diagnostics in valuation; draft spread/optional-key, update and variable-reuse issues remained |
| final-valuation-records-types-02.log | native 1: five remaining valuation top-level return diagnostics, down from 40 |
| final-valuation-records-test-types-01.log | native 1: focused command lacked API import path; not a valid whole-gate comparison |
| final-valuation-records-test-types-02.log | native 1: correct import path, four existing P&L test annotations missing |
| final-valuation-records-test-types-03.log | native 1: typed helper exposed two nullable aggregate assertions; explicit availability assertions added |
| final-valuation-records-focused-types-01.log | native 1: test imported a non-exported module attribute; corrected to defining module |
| final-valuation-records-focused-types-02.log | native 0: six strict files |
| final-valuation-records-positive-01.log/xml | native 0: 189 passed, three warnings, 29.67s |
| final-valuation-records-positive-02.log/xml | native 0: 290 passed, three warnings, 31.31s across 17 affected files |
| final-valuation-records-parity-01.log | native 0: twelve complete valuations match frozen fcaa774 values, scalar representations and JSON field order |
| final-valuation-records-format-01.log | native 0: 343 files formatted |
| final-valuation-records-ruff-01.log | native 1: one import-spacing issue; correction pending |
| final-valuation-records-no-execution-01.log | native 0: no executable broker actions |

Whole strict 58 native 1, also retained in .exit: 539 raw/canonical diagnostics,
63 files, 322 source files, nine distributions. API: 253 / 13 / 125. Observed
2026-09-12T15:00:54.370374+00:00. Forty-seven fewer diagnostics than run 57,
zero new diagnostics after normalizing line shifts. Parity cases: cash-only,
long, short, closed, zero-price write-off, missing price, missing FX, foreign
cash, precision balance adjustment, missing benchmark, spin-off and 100-date
aligned risk history with available beta. No frontend application changes.
Browser connection attempt again failed before execution (sandbox metadata);
the existing isolated Node 22 Playwright runner is being used. Browser receipt
and final static correction remain pending. No full release pass claimed.

Final valuation-record verification:
- Browser 01 native 0: five passed, zero skipped/flaky/global errors, 116.877422s,
  start 2026-09-12T15:01:29.379Z. Command: Node 22 Playwright test
  tests/e2e/operating.spec.ts tests/e2e/trade-monitor.spec.ts
  tests/e2e/risk-availability.spec.ts. Isolated run ID
  final-valuation-records-browser-01; .log/.exit/-results.json retained. All 16
  screenshots inspected, including five overview sizes, seven operating desks,
  two saved trade reviews and two explicit unavailable-risk states. API log:
  zero traceback/500/database-lock matches. No Firefox or full-suite claim.
- Ruff 01's one spacing issue corrected by the import formatter. Ruff 02 and
  format 02 native 0, 343 files. OpenAPI 01 native 0, 170 paths.
- Negative 01 native 1: new tests run against frozen fcaa774 valuation module,
  six failed, one passed, one warning, 1.30s. Each failing case reproduced
  TypeError subtracting an unavailable posting total. No active data changed.
- Positive 03 native 0 after final import correction: 54 passed, one warning,
  2.87s, three files; .log/.xml retained. The seven new cases are included in
  the earlier 290-test run. Full current backend and deployment remain pending.
