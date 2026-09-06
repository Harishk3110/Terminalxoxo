# Build Evidence 25K

Baseline: c3d9e847604fbbfb59df170c1b5f83f7dbec94a1. Date: 2026-09-06.

| Command | Commit | Exit | Result |
| --- | --- | ---: | --- |
| git status --short --branch | c3d9e84 | 0 | Clean main tracking origin/main before edits |
| git branch --show-current | c3d9e84 | 0 | main |
| git rev-parse HEAD | c3d9e84 | 0 | Baseline hash verified |
| git log --oneline -10 | c3d9e84 | 0 | Existing history retained |
| git remote -v | c3d9e84 | 0 | Existing Terminalxoxo origin retained |
| python scripts/count_25k_delta.py --inventory --output docs/25k/baseline-inventory.json | c3d9e84 + worktree | 0 | Baseline source/route/endpoint/test inventory captured |

## Accounting Foundation, 2026-09-06

All commands below used C:/Dev and c3d9e84 plus the current uncommitted worktree.
Python commands use `.venv-sprint/Scripts/python.exe`, unless stated otherwise.

| Command | Exit | Result |
| --- | ---: | --- |
| -m pytest tests/sprint/test_loc_counter.py -q | 0 | 55 passed |
| -m pytest tests/sprint services/api/tests/test_portfolio_accounting.py --cov=app.portfolio_domain --cov-report=term-missing -q | 0 | 147 passed; domain 95% coverage at this checkpoint |
| -m pytest services/api/tests -q | 0 | All 66 baseline backend tests passed |
| -m pytest tests/sprint/test_portfolio_resources.py tests/sprint/test_ledger_revisions.py -q | 0 | 41 resource/correction integration tests passed |
| -m pytest tests/sprint -q | 0 | 228 passed before migration test addition |
| -m pytest tests/sprint/test_ledger_migrations.py -q | 0 | 5 fresh/upgrade/downgrade/constraint tests passed |
| corepack pnpm --filter @knk/terminal-web test | 0 | 27 tests, including 9 rendered control workflows |
| corepack pnpm --filter @knk/terminal-web typecheck | 0 | TypeScript passed |
| -m mypy --follow-imports=silent (15 new Python source files and LOC counter) | 0 | Strict project configuration; imported legacy modules not checked |

The exact mypy inputs were `services/api/app/schema.py`, `ledger_models.py`,
`ledger_contracts.py`, `ledger_revisions.py`, `lot_persistence.py`,
`portfolio_resources.py`, `portfolio_resource_api.py`, `portfolio_domain`, and
`scripts/count_25k_delta.py` (app filenames relative to services/api/app).

Failures found and corrected: weighted-average full disposal left Decimal dust;
no-op correction compared serialized Decimal scales; a resource method shadowed
the list type; jsdom needed test-only native-dialog method substitutes; two test
locators used an unsupported React Testing Library option. None are omitted from
the work history or represented as passing prior to correction.

Migration 0001 now freezes its pre-sprint table ownership, because dynamically
creating all current ORM tables would create revision 0004 tables prematurely.
Migration 0004 uses explicit DDL and reversible constraints/indexes. Existing
portfolio rows survived the temporary-database downgrade/upgrade test.

## Accounting Checkpoint, 2026-09-06 11:24 UTC

Source checkpoint: e25b94e52a7669458beaaa8c7685942dc256cd55, pushed to the existing
Terminalxoxo origin/main. Verification below preceded the commit; source is identical.

All results below use the baseline plus the checkpoint worktree, not the old API
process on port 8000. Test servers use isolated databases and ports 8001/3002.

| Command | Exit | Result |
| --- | ---: | --- |
| -m pytest tests/sprint services/api/tests --cov=app.portfolio_domain --cov=app.ledger_revisions --cov=app.portfolio_resources --cov=app.portfolio_resource_api --cov=app.accounting_persistence --cov=app.portfolio_balances --cov-report=term-missing --cov-report=json:logs/sprint-accounting-coverage.json -q | 0 | 369 passed; 98% targeted coverage, 1,069 statements, 23 missing; three existing deprecation warnings |
| -m pytest tests/sprint/test_ledger_migrations.py -q | 0 | 15 tests, including fresh head, downgrade/upgrade, schema parity and CHECK enforcement |
| corepack pnpm --filter @knk/terminal-web test | 0 | 52 tests; API proxy/client, draft contracts and rendered controls |
| KNK_NEXT_DIST_DIR=logs/sprint-25k-build corepack pnpm --filter @knk/terminal-web build | 0 | Production build and typecheck passed; terminal route 93.5 kB / 186 kB first load |
| PLAYWRIGHT_DIST_DIR=logs/sprint-25k-build PLAYWRIGHT_RUN_ID=sprint25k-ledger-4 corepack pnpm exec playwright test tests/e2e | 0 | All 16 browser tests passed |
| PLAYWRIGHT_DIST_DIR=logs/sprint-25k-build PLAYWRIGHT_RUN_ID=sprint25k-ledger-5 corepack pnpm exec playwright test tests/e2e/ledger.spec.ts | 0 | Four ledger workflows passed after CSS header fix, with screenshots at 1366/1440/1920/2560/390 widths |
| -m ruff check (new accounting modules, sprint tests, migrations 0004/0005, LOC counter) | 0 | All checks passed |
| -m mypy --follow-imports=silent (19 source files) | 0 | Strict targeted checks passed; legacy imported implementations excluded |
| corepack pnpm security-check | 0 | No forbidden broker action method names in application source |
| scripts/count_25k_delta.py --baseline c3d9e847604fbbfb59df170c1b5f83f7dbec94a1 --output docs/25k/current-delta.json --check | 1 | Expected: only 4,940 qualifying lines; all category floors remain unmet |
| GET http://127.0.0.1:8000/health/ready | 0 | Old API/database ready, Redis TimeoutError, local object storage ready |
| docker info / docker ps | 0 | Daemon 29.4.2 available; no running containers |

Additional strict mypy inputs: `accounting_models.py`, `accounting_persistence.py`,
`portfolio_balances.py` and `portfolio_domain/postings.py` under services/api/app.

Windows commands set environment variables with `$env:NAME='value'` before the
listed command; the compact table notation is not a PowerShell command literal.

Failures found through browser verification and fixed: Next's proxy lacked PUT
and DELETE forwarding (405); table headers lacked explicit column scope; native
dialog dismissal did not restore launch-button focus; globally fixed table layout
compressed mobile headers into adjacent columns. The ledger now uses auto-sized
columns inside its scroll container, with a browser header-overflow regression check.

Manual screenshot inspection confirmed the corrected accounting table at mobile
390x844 and desktop 1440x900. Committed examples: `25k/activity-390.png` and
`25k/activity-1440.png`. The five-size policy/cash/lots/activity/balance captures
and reversal/correction captures remain in `logs/ledger-screenshots` locally.

## Saved Data Rehearsal

`verify_portfolio_release.py inventory` captured the original database before any
migration. A consistent untouched backup is `logs/pre-sprint-ledger-backup.sqlite`.
A fresh copy, `logs/sprint-subledger-final.sqlite`, upgraded from 0003 through 0005.
Forced valuation on that copy returned NAV SGD 70,597.57, knk-nav-4.1, four persisted
lots and eight persisted accounting components. NAV and component reconciliations
both returned BALANCED. The comparison tool retained every original record hash:
16 transactions, nine details, two datasets, two versions, one analysis run and
22 prior valuation runs. The new run increased the copy's run count to 23.
The preservation report is `logs/sprint-subledger-final-preservation.json`.

No real-database migration, user-web deployment, full-stack health, whole-app 85%
coverage, completed M1 or completed 25K sprint is claimed by this checkpoint.

## Storage Boundary Follow-Up, 2026-09-06 11:38 UTC

The same combined Python/coverage command now passes 395 tests: 1,079 targeted
statements, 23 missing, 98%. Strict mypy still passes for the 19 targeted files.
Ruff passes for the changed domain/contracts/revision/balance/test files; the
touched legacy operations module passes E9/F checks (not a whole-module Ruff claim).
Playwright's full 16-test suite passed again with run ID sprint25k-ledger-6.
No frontend implementation changed after its successful production build/52 tests.
The LOC check correctly exits 1 at 5,054 eligible lines; all floors remain unmet.

The NUMERIC(24,8) write boundary now rejects excessive input precision and derived
gross amounts that cannot be represented. Provider-resolved FX is explicitly
half-even rounded to eight places with observed and recorded rates in protected
metadata. Explicit user FX is not silently rounded. Stored base-value projections
use half-even eight-place rounding. SQLite driver round-trip checks reject large
fractional values whose binary representation would change a recorded input.
This deliberately rejects unsupported values rather than expanding storage scale.

A replay regression test initially compared Decimal string scale (`10000` versus
`10000.00000000`); it now compares every reconciliation numeric value as Decimal.
Supported fractional inputs retain quantity, gross, commission and NAV after a
fresh database read. Broader precision/storage architecture remains an open M1/M18
task; these tests are not certification of all PostgreSQL or SQLite accounting.

## Transaction Context and Entry Views, 2026-09-06 12:18 UTC

The new context contract validates aware trade timestamps, original external
references, broker references and strategy/thesis links. It normalizes timestamps
to UTC, rejects future/inconsistent timestamps and non-printable reference
characters, and reads creator identity from the creation audit rather than client
metadata. Legacy missing or malformed fields remain unknown with warnings; their
original metadata is not rewritten. Broker references never imply confirmation.

Transaction cash effects now come from actual ledger movements. Source-currency
net cash, base-valued source cash, all-leg base cash and individual native legs
are distinct. This covers FX conversions, cash mergers and non-cash actions;
voided or not-yet-effective historical entries report NOT_REPLAYED, not zero.

The Trade Monitor's old form is replaced by the typed 19-kind ledger form. Its
portfolio-scoped options provide accounts, policy, currencies and research links.
Hidden fields do not leak into unrelated transaction types, standalone expenses
do not double-submit charges, and source/destination FX currencies stay distinct.
The existing black/amber shell and separate Portfolio-page manual flow remain.

| Verification | Exit | Result |
| --- | ---: | --- |
| Combined Python command from the prior checkpoint, additionally --cov=app.transaction_context --cov=app.transaction_views | 0 | 442 passed, three existing deprecation warnings; targeted 98%, 1,194 statements, 24 missing |
| corepack pnpm --filter @knk/terminal-web test | 0 | 103 passed, including 38 entry-payload cases and 13 rendered entry/detail tests |
| corepack pnpm test-unit | 0 | Same 103 frontend tests plus three domain and two function-registry tests; package echo scripts receive no test credit |
| KNK_NEXT_DIST_DIR=logs/sprint-25k-build corepack pnpm --filter @knk/terminal-web build | 0 | Final frontend build and typecheck; route 96.1 kB / 188 kB first load |
| PLAYWRIGHT_DIST_DIR=logs/sprint-25k-build PLAYWRIGHT_RUN_ID=sprint25k-entry-2 corepack pnpm exec playwright test tests/e2e | 0 | All 18 browser tests passed on final frontend, including entered timestamp persistence, all entry modes and audit detail at five viewport sizes |
| Ruff, new modules and sprint tests | 0 | Full targeted check passed; legacy operations/API/valuation checked with E9/F |
| Strict mypy with --follow-imports=silent | 0 | 22 targeted source files; includes transaction_context.py, transaction_views.py and portfolio_domain/transaction_cash.py |
| corepack pnpm security-check | 0 | No forbidden broker action method names |
| LOC counter with --check | 1 | Expected: 6,275 qualifying lines, every category floor still unmet |

The first full browser attempt (sprint25k-entry-1) passed 17 and failed one older
workflow because its exact lowercase `price` locator no longer matched `Price`.
The locator was corrected without removing its record/review assertions. The
final rerun passed that workflow and the remaining suite. The mobile datetime
input was widened after screenshot review; a width assertion now protects it.
The final malformed-legacy-reference read guard was added during browser startup
and is covered separately by the final 442-test Python run.

Evidence images: `25k/entry-buy-390.png`, `25k/transaction-details-390.png`,
`25k/transaction-details-1440.png`. Local five-size captures and test logs remain
under logs/ledger-screenshots and logs/e2e-sprint25k-entry-2-*.log. Screenshot
inspection confirmed legible wrapping and no overlapping audit fields.

The previously migrated backup copy, logs/sprint-subledger-final.sqlite, revalued
at SGD 70,597.57 under knk-nav-4.2, with both reconciliations BALANCED. All nine
main-portfolio transactions include context/cash states. The preservation report
logs/sprint-context-preservation.json retains every original hash, including all
16 transactions across portfolios and 22 prior runs; the copy now has 24 runs.
The real database remains unmigrated and the user-facing web is not deployed.

Remaining M1 gaps include full position metrics and corporate-action daily P&L,
broader storage precision, portfolio-creation UI and permitted live migration.
Trade timestamps are provenance only, not an intraday matching-order claim.
No milestone or 25K acceptance certification is implied by this checkpoint.

## Position-Period P&L, 2026-09-06 12:30 UTC

Source predecessor: c770947a04b3b169332f0ff6442780b5db06d99a, pushed. The current
position_pnl.py is integrated into every valuation interval under knk-nav-4.3.
It replaces the transaction-label cash approximation with actual replay cash,
external security capital and paired internal corporate-action transfers.
Zero holdings and missing opening/closing marks are distinct. Closed-position
income and cash merger consideration are retained in daily attribution.

The declared attribution convention transfers reference value using the recorded
cost-allocation fraction. Intraday buys enter reference value at gross recorded
consideration; partial closes remove reference value proportionally to units.
This is an explicit internal allocation convention, not a claim that cost fractions
always equal fair-value fractions or that M2 Brinson attribution is implemented.
Internal transfers sum to zero and cannot create portfolio P&L.

- 24 domain tests passed, including Hypothesis conservation checks, shorts,
  partial/full closes, standalone expenses, security transfers, stock/cash mergers,
  spinoffs into new/existing positions, unknown marks and duplicate interval records.
- Four API tests passed: merger attribution ties to NAV and saved payload;
  spinoff value transfer is not treated as gain; income on a closed position is
  retained; unavailable prior marks remain null rather than becoming zero.
- Full combined Python/coverage command from the preceding section: exit 0,
  470 passed, three existing warnings, 98% targeted coverage (1,308 statements,
  26 missing). position_pnl.py coverage is 97%, with three defensive branches uncovered.
- Strict mypy with silent imported legacy implementations: exit 0, 23 source files.
  Ruff for the new module/tests and E9/F for the touched valuation module: exit 0.
- Full Playwright suite: exit 0, 18 passed, run sprint25k-pnl-1, using the unchanged
  final frontend build in logs/sprint-25k-build. Its version assertion is knk-nav-4.3.
- LOC --check: expected exit 1, 6,619 qualifying lines; all category floors unmet.

The migrated backup copy revalued at SGD 70,597.57, BALANCED, with four position
component states AVAILABLE and latest daily P&L zero on the unchanged stale marks.
All original immutable hashes survived; the copy now contains 25 valuation runs.
Evidence: logs/sprint-position-pnl-preservation.json. No real database or user-facing
service was migrated/restarted. M1 and the overall sprint remain incomplete.

## Position Measurements and Inspector, 2026-09-06 12:50 UTC

Source predecessor: bef7c5cc84b8efbbc61382ca3adc0f8d96d2135f, pushed.
knk-nav-4.4 separates signed native/base market values and recorded cost bases,
with unrealised price and FX components that reconcile algebraically. Missing FX
does not erase native value; a known zero price is distinct from a missing mark.
NAV and sector weights use unrounded marked values. Beta contributions remain
unavailable when the underlying beta is unavailable.

The accounting position inspector exposes valuation, daily components, separate
price/FX provenance and open lots. Its API reads the parent's saved run, rejects
cross-portfolio run IDs and conflicting date/run selectors, and does not reprice
historical payloads. Legacy snapshots explicitly report absent breakdowns.

- Combined Python/coverage command from the earlier checkpoint: exit 0, 498 passed,
  three existing warnings. Targeted coverage 98%, 1,412 statements, 26 missing;
  position_metrics.py 100%. This is not whole-application coverage.
- Added 23 domain tests and five API tests, including property-based signed FX
  decomposition, missing marks, saved-run immutability and portfolio ownership.
- Frontend Vitest: exit 0, 113 passed, including nine inspector cases and one
  accounting-dialog integration case. Typecheck passed.
- Production build: exit 0, terminal route 98 kB / 190 kB first load.
- Full Playwright: exit 0, 19 passed in 3.9 minutes, run sprint25k-position-1.
  The inspector check covers all five viewport sizes, four views, run pinning,
  security switching, overflow and focus restoration without browser errors.
- Ruff passed on touched new domain/resource modules and tests. Strict mypy with
  silent legacy imports passed on 24 source files. Security check passed.
- LOC --check: expected exit 1, 7,423 qualifying lines; all floors remain unmet.

Reviewed captures: 25k/position-value-390.png, 25k/position-daily-390.png,
25k/position-sources-1440.png. The mobile values wrap within their grid and the
desktop source panel separates imported prices from demo FX without a live claim.
Full local captures remain in logs/ledger-screenshots.

Backup-copy replay remains SGD 70,597.57, BALANCED, four marked positions AVAILABLE.
logs/sprint-position-metrics-preservation.json verifies all original immutable
hashes; there are now 26 copy valuation runs. The real database remains untouched.
No user-facing deployment or milestone completion is claimed. Broader storage
precision, portfolio creation UI, exposure coverage and M2-M20 remain unfinished.

## Portfolio Directory, 2026-09-06 13:05 UTC

Source predecessor: 8ac83a42153845dd9cc6c2b190d165355761180f, pushed.
Home now opens a scoped internal-ledger directory. Creation records explicit
opening capital, currency, benchmark, date and cost policy, with a real opening
deposit and audit event. Creation options come from configured currencies and
the security master. The date boundary is explicitly the existing server UTC
rule, not a new exchange-calendar or Singapore business-date claim.

Selected-ledger accounting, transaction entry and corrections share that ledger's
ID and return to its directory context. Mutations refresh the scoped transaction
list. The main dashboard remains KNK_MAIN; directory selection is not a global
portfolio switch. The creation form blocks cancellation while its write is pending.

- Full combined Python/coverage command: exit 0, 512 passed, three existing
  warnings. Targeted coverage 98%, 1,418 statements, 25 missing.
- 14 additional API tests cover options without KNK_MAIN, exact persisted capital,
  policy flags, duplicate/unsafe-write rollback and separate-ledger NAV/ownership.
- Frontend Vitest: exit 0, 131 passed, including eight creation and ten directory
  cases. Typecheck passed. The 131 test count is unrelated to the user's 131
  acceptance steps, which are NOT certified by this result.
- Production build: exit 0, route 101 kB / 193 kB first load.
- Full Playwright: exit 0, 21 passed in 4.3 minutes, run sprint25k-directory-1.
  New browser checks cover five viewport sizes, non-nested dialog navigation,
  opening capital, a USD deposit and correction, reload persistence and unchanged
  KNK_MAIN transactions/NAV. Existing stress/backtest/login workflows also passed.
- Ruff and strict mypy (24 targeted source files with silent legacy imports):
  exit 0. Broker-execution security check passed. LOC --check expected exit 1:
  8,227 qualifying lines, all category floors still unmet.

Reviewed images: 25k/portfolio-directory-1440.png, 25k/portfolio-create-390.png,
25k/portfolio-created-390.png. Tables scroll horizontally on mobile within the
dialog; creation fields and ledger summaries remain inside the viewport.
Two test-only assertions were corrected before the final passing runs: comparison
before/after session expiration now uses persisted Decimal representations, and
the BUY correction test locates Price rather than a cash-only Gross amount field.

No new migration was needed. Earlier backup-copy preservation evidence remains
valid for unchanged knk-nav-4.4; no real portfolio was created or mutated by tests.
The isolated servers stopped after the run; only the earlier baseline API on 8000
remains. User-facing deployment, M1 certification, broader precision/exposure work,
M2-M20 and all final gates remain incomplete.

## Correction Storage and Provenance, 2026-09-06 13:12 UTC

Source predecessor: bb8812fd99420534498ac62af36764cafb97f35f, pushed.
The existing driver round-trip guard is shared through ledger_storage.py rather
than copied; moved lines receive no extra LOC credit. Corrections now reject
the same unsafe numeric fields and out-of-range projected base values as new
entries. The exact JSON revision remains the audit record, not a silently rounded
replacement. FX corrections identify their manual origin; original provider
rounding remains in the before snapshot. Voids retain last-corrected display
values while contributing no replay cash.

Twelve regression cases were added. Before the fix, nine failed as expected:
seven input-driver boundaries, one derived base limit and one false FX provenance.
The final complete backend suite passes 524 tests with three existing warnings.
Coverage now includes --cov=app.ledger_storage: 98% targeted, 1,449 statements,
26 missing. Ruff and strict mypy passed on 25 targeted source files; security
check passed. No PostgreSQL runtime certification is inferred from SQLite tests.

Focused Playwright command (ledger.spec.ts and portfolio-directory.spec.ts):
exit 0, six passed, run sprint25k-correction-1. No frontend changes or rebuild
were needed; the last full 21-browser-test run and 131 frontend tests are from
bb8812f. LOC --check expected exit 1: 8,331 qualifying lines, all floors unmet.
No migration or real-data mutation occurred. Broader derived snapshot precision,
exposure/freshness coverage, all milestone certifications and final gates remain open.

## Grouped Exposures and Cash Freshness, 2026-09-06

Source predecessor: 1318447728acfac59058bb3e444b3521c86f68a8, pushed.
knk-nav-4.5 preserves unavailable groups instead of dropping them, and retains
exact marked values before display rounding. Group results separate long/short,
cash, net outstanding manual balances, net/gross values and signed NAV weights.
Currency and asset-class partitions include cash and balances; country and sector
remain position-only. Economic cash already includes settlement balances, so
settlement receivables/payables are not added again to exposure.

Freshness now includes absolute stale cash-FX and outstanding-balance values.
Reversals are netted by native bucket/currency before marking. Missing components
make the stale-NAV ratio unavailable; zero NAV is not a zero ratio, and leverage
can legitimately produce a ratio above 100%. Base-currency cash-only valuations
are CALCULATED, not incorrectly classified DEMO by an empty source-category set.

GET /api/v1/portfolios/{id}/exposures is scoped and supports run_id or end,
rejecting both together. Saved runs are read without current repricing. Legacy
snapshots retain old aggregate values but explicitly lack new components.
The accounting Exposures view presents groups, freshness and balance FX marks.

Connected broker presentation now constructs an explicit metadata allowlist;
internal lots, transactions, accounting, exposures and valuation identities are
not inherited into broker-reported results. Internal NAV remains separately
labelled only for reconciliation. This adds no broker write capability.

Verification:
- Initial complete backend run: 566 passed; targeted accounting coverage 98%,
  1,558 statements and 26 missing. Exposure domain and adapter both 100% statements.
- Broker boundary plus existing broker/agent regressions: seven passed.
- A subsequent full rerun exposed the existing wall-clock-minute fingerprint
  problem (567 passed, one historical-cache identity failure). Historical
  fingerprints now omit the wall-clock epoch; current-day freshness still
  refreshes each minute, and source changes/force still invalidate. The failing
  case and three deterministic cache tests pass. Final full rerun: 571 passed,
  three existing deprecation warnings, unchanged targeted coverage, 236.62 seconds.
- Frontend: 143 Vitest tests pass, including two explicit detail-query refresh
  recovery cases. Build and separate typecheck pass; terminal
  route 102 kB, first load 194 kB. Final output logs/sprint-25k-exposure-build.
- Full Playwright: 22 passed, run sprint25k-exposure-1, before the final CSS and
  broker-boundary follow-up. Screenshot review then found wrapped controls
  clipped by a fixed 29px strip. Ledger strips now expand and visibly mark the
  selected mode. The stronger final browser run passes all eight affected ledger,
  position, directory and exposure workflows, run sprint25k-exposure-final.
  That run preceded the historical-cache and explicit-refresh fixes, covered by
  backend and frontend unit tests. The final exposure refresh browser case passed
  at all five widths (sprint25k-exposure-refresh, one test, 1.8 minutes).
- Ruff checks and strict mypy passed on 27 audited source files. Legacy valuation
  and broker modules pass E9/F checks; this is not whole-repository strict typing.
  Broker-execution security scan passed; LOC --check correctly exits 1.

Screenshots reviewed: 25k/exposure-currency-1440.png,
25k/exposure-currency-390.png, 25k/exposure-freshness-390.png. Tables scroll inside
the dialog and every accounting control fits its strip at all five target widths.
Test-only mistakes in the first draft (deposit amount field, Vitest hook return,
rerender provider, unsupported testing-library option and placeholder assertions)
were corrected before final verification.

The existing migrated backup copy replayed with NAV SGD 70,597.57, BALANCED,
and all captured original record hashes retained. Preservation comparison:
logs/sprint-exposure-preservation.json, 16 transactions, nine details, two dataset
versions, one analysis run and 27 copy valuation runs. No schema change or real
database mutation occurred. Isolated servers stopped; only baseline API 8000
remains. No user-facing deployment or complete milestone is claimed.

Qualifying delta: 9,357, all category floors unmet. Next financial work is the
NAV balance-sheet presentation of short liabilities/overdrafts, remaining derived
storage and metric contracts, then M2 performance/attribution. M1-M20 certification
and all final acceptance gates remain incomplete.

## Urgent Wrap-up, 2026-09-07 SGT

Source predecessor: a008de5f711b198d0056c1d10e49b32c397f283e. Existing main/origin
retained. Product expansion is paused by the user; the 25K sprint is NOT complete.
The containing commit preserves the saved NAV statement, exact Decimal display,
balance-sheet decomposition and the partial performance service. Performance is
explicitly IN DEVELOPMENT, not a certified M2 implementation. No broker execution
method was introduced. No source, database or user data was reset.

Deployment preparation:
- Next.js and eslint-config-next upgraded to 15.5.24, React 18 retained. Both apps
  target Node 22, pnpm 9.15.4 and the existing workspace lockfile. App-root builds,
  shared-package transpilation and repository-root output tracing are configured.
- Missing/loopback production API origins fail configuration. Local builds need
  explicit local/test mode. Browser API calls remain same-origin `/backend`;
  provider credentials are never injected into public environment variables.
- Public Tailwind now uses an explicit config path and app-relative content globs.
  Visual review caught stale, unstyled CSS despite an HTTP 200 and successful build.
  A fresh diagnostic build and final default `.next` rebuild include the utilities.
- Docker uses Node 22 and frozen-lockfile installation. Compose reads ignored
  credentials instead of source constants. It requires configuration before use;
  existing persistent-volume credentials must be retained.
- Generated test PNGs were untracked, not deleted from disk. SQLite files, runtime
  directories, secrets and local Vercel metadata remain ignored.

Verification during this wrap-up:
- `corepack pnpm install --offline --frozen-lockfile`: exit 0.
- Workspace frontend lint and typecheck: exit 0. Frontend Vitest: 228 passed in
  14 files. Shared package test commands also passed; echo-only scripts are not tests.
- Node 22 app-directory `next build`: both exit 0. Terminal route 117 kB / first
  load 224 kB; public route 3.46 kB / first load 106 kB. No local API access is
  required to produce either frontend build; the terminal validates configuration.
- Full Python suite: 643 passed, three existing deprecation warnings, 166.42s.
  Final performance API follow-up: seven passed after the IN DEVELOPMENT label.
- Targeted strict mypy: 36 files passed. Targeted Ruff passed. Whole-backend Ruff
  still has 227 findings; whole-backend mypy has 630 errors in 23 of 62 checked
  files. These legacy-wide failures were not suppressed or represented as passing.
- FastAPI import passed with 142 routes. Alembic has one head,
  0005_accounting_subledgers. No-broker-execution and secret/artifact scans passed.
- Final post-Next-update Playwright: 23 passed, zero skipped/flaky/unexpected,
  210.62s, run wrapup-next15-final. Evidence is local logs/terminal-e2e-results.json.
  The first post-update run failed because the isolated server lacked explicit test
  mode; the supported harness now supplies it. No forbidden user-server launch
  was attempted via the harness.
- Public standalone browser checks: HTTP 200 and seven asset HTTP 200 responses
  at 1440px and 390px, expected computed styles, no horizontal overflow, no fatal
  runtime errors or HTTP failures. Screenshots reviewed locally. An initial check
  counted prefetch cancellations on page navigation; separate-page verification
  avoids treating intentional navigation cancellation as an application failure.
- Compose configuration validation passed using temporary process-only values and
  `--no-env-resolution`; Docker Linux daemon unavailable, so no container health
  or new image runtime certification is claimed.

Local API /health/live returns 200 in local-demo. The real database was backed up,
then migrated from 0003 to 0005. All original record hashes were retained: 16
transactions, nine details, two datasets, two versions, one analysis run and 22
original valuation runs. A new real NAV run is knk-nav-4.6, SGD 70,597.57, ledger
and balance sheet BALANCED; original opening SGD 70,000 retained.

Private port 3001 remains unreachable: the agent's supported server launch was
blocked by execution policy, and no alternative launch was used to bypass it.
Firefox was not opened onto an unverified terminal URL. The user must run the
updated OPEN-KNK-TERMINAL.cmd. Public port 3000 and API 8000 remain running.
In-app browser bootstrap was unavailable; existing Playwright and standalone
Chromium verification were used after that failure was reported.

Vercel CLI 59.11.7 reports Logged out; no project links or public production API
were found. No deployment URL is fabricated. Exact two-project import settings
and backend hosting requirements are in PRODUCTION_HOSTING_STATUS.md.

Final LOC report: 10,639, all category/total gates unmet; `--check` exits 1 as
expected. This is an honest runnable-source checkpoint, not production or full
milestone certification. Final handoff records commit/push and endpoint rechecks.
