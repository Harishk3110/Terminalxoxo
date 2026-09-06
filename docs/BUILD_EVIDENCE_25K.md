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
