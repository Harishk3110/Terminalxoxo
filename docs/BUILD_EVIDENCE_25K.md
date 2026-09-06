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
