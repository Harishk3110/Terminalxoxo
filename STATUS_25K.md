# STATUS 25K

## Current Wrap-up

Superseded by the terminal-only scope correction. See STATUS.md and
docs/PRD_TERMINAL_ONLY.md; the following wrap-up is retained as historical evidence.

New product expansion is paused at the user's urgent wrap-up request, 2026-09-06.
The 25K sprint remains incomplete. Do not resume feature expansion without direction.
Current branch main; current predecessor a008de5f711b198d0056c1d10e49b32c397f283e.
Current conservative count: 10,639 (backend 3,056; frontend 2,161; infrastructure
296; tests 5,126). Every category gate remains unmet.

Both frontend apps build on Node 22 with Next.js 15.5.24 from their own app folders.
Frontend lint/type checks and 228 frontend tests pass; 643 Python tests pass.
Strict checks pass on 36 targeted source files. Whole-backend checks do NOT pass:
227 Ruff findings and 630 mypy errors across legacy code. They are not hidden.
The final post-update Playwright run passed all 23 tests, including saved NAV
statement and exact display checks. No skipped or flaky tests were reported.
Public-site Tailwind configuration was corrected after visual review found stale,
unstyled output. The final default-directory build renders correctly at 1440/390px.

API port 8000 is live; public website port 3000 and static assets return HTTP 200.
Terminal port 3001 launch was blocked by execution policy. No bypass was attempted.
Firefox has not been opened because that terminal URL is not yet verified.
Real database backed up to logs/pre-wrapup-backup.sqlite, upgraded to 0005, and
all original hashes retained. No reset or source deletion occurred.

Vercel CLI is logged out; no linked projects or production API were found.
Docker Linux engine is unavailable. No cloud deployment or full-stack health is claimed.
See docs/PRODUCTION_HOSTING_STATUS.md for exact Vercel settings and remaining services.
Generated screenshots were removed from Git tracking, not from disk; secrets and
runtime artifacts remain excluded. The containing commit preserves the wrap-up;
the final handoff records publication and post-push HTTP verification separately.

## Historical Checkpoints

The following notes describe earlier sprint checkpoints, not current service state.

Sprint active. Baseline: c3d9e847604fbbfb59df170c1b5f83f7dbec94a1.
Initial verified checkpoint: e25b94e52a7669458beaaa8c7685942dc256cd55, pushed to origin/main.
Storage-boundary checkpoint: e5f5d43282d1f6f63c22e0eeec954155ee634eaf, pushed.
Transaction-entry checkpoint: c770947a04b3b169332f0ff6442780b5db06d99a, pushed.
Position-period checkpoint: bef7c5cc84b8efbbc61382ca3adc0f8d96d2135f, pushed.
Position-inspector checkpoint: 8ac83a42153845dd9cc6c2b190d165355761180f, pushed.
Portfolio-directory checkpoint: bb8812fd99420534498ac62af36764cafb97f35f, pushed.
Correction-storage checkpoint: 1318447728acfac59058bb3e444b3521c86f68a8, pushed.
Exposure checkpoint: a008de5f711b198d0056c1d10e49b32c397f283e, pushed.
Current change: exact decimal display and saved NAV balance sheet; `git rev-parse HEAD` resolves this checkout.
Branch main; existing origin retained. No sprint milestone is certified complete.

- Current milestone: M1 in progress, audited ledger and accounting subledgers implemented.
- Qualifying delta at 2026-09-06 14:09 UTC: 9,858 conservative novel source/test lines.
  Backend 2,474; frontend 2,144; workers/agents/reports/infra 263; tests 4,977.
  This is an interim worktree count, not a milestone certification.
- Gates: backend 9,000; frontend 6,000; infrastructure/agents/reports 3,000;
  substantive tests 7,000; total 25,000.
- Services: prior local API PID 30820 on 127.0.0.1:8000 still serves baseline code.
  Readiness reports API/database ready, Redis TimeoutError and local object storage ready.
  No listener on 3001. Isolated Playwright servers on 8001/3002 stopped after tests.
- Operational routes/APIs: portfolio resources added, including append-only
  corrections, scoped lot details, accounting policy, cash, recalculation,
  historical-run accounting components and append-only balance adjustments.
- Tests: combined Python suite 594 passed, including all 66 existing backend tests;
  targeted accounting coverage 98% (1,571 statements, 26 missing), not whole-app coverage.
  Final NAV API follow-up: seven passed. Frontend 201 passed; typecheck passed.
  Current full browser and production-build verification pending below.
  Repository test-unit command also passes five shared-package tests; other package echo scripts are not tests.
  Full Playwright suite 22 passed with knk-nav-4.5 (sprint25k-exposure-1).
  Eight affected workflows passed after the mobile strip/broker follow-up
  (sprint25k-exposure-final); this preceded the historical-cache and explicit
  refresh follow-ups, covered by backend/frontend unit tests. The final exposure
  refresh browser case passed at all five widths (sprint25k-exposure-refresh).
  Final frontend build: logs/sprint-25k-exposure-build.
- New Python modules: Ruff and strict mypy passed on 27 source files (legacy imports silent).
- Migrations 0004/0005 passed 15 lifecycle/schema/constraint tests. A fresh saved-data
  backup copy upgraded from 0003 to 0005, valued at SGD 70,597.57, and retained all
  captured original hashes (16 transactions, two dataset versions, 22 prior runs).
  The user's real knk_terminal.db has NOT been migrated; no live deployment is claimed.
- Frontend: Home accounting dialog and Trade Monitor corrections integrated;
  Activity and Balances now expose persisted components and audited adjustments.
  Trade Monitor entry covers all 19 transaction kinds, account/research references,
  optional aware timestamps, corporate-action fields and exact decimal payload strings.
  Details expose original references, creator provenance and replay-derived cash legs.
  Desktop/mobile screenshots: docs/25k/transaction-details-1440.png,
  transaction-details-390.png and entry-buy-390.png, plus prior accounting captures.
- Docker: daemon 29.4.2 responds; docker ps lists no running containers.
  This is not complete-stack health. User-facing web launch was denied earlier;
  no alternative server launch was used to bypass that denial.
- Blockers: none for demo/domain/contract implementation. Live credentials absent
  are not treated as blockers.
- First unchecked execution task: finish M1 derived-storage precision and
  remaining persisted metric contracts. Audit timestamps are
  provenance only; same-day replay order remains the original ledger record order.
  Audit references are not yet editable through the correction dialog.
  Live additive migration, permitted service deployment and M1 certification remain.
- Existing storage contract is now explicit: inputs and derived gross must fit eight
  decimals; provider FX rounding is recorded, and unsafe SQLite round-trips are rejected.
  This is a safety boundary, not expanded precision support or a production DB certification.
- Position daily P&L now uses recorded cash movements, explicit external security
  flows and paired corporate-action reference transfers. Closed-position income is
  retained, and missing opening marks cannot create artificial daily gains.
  Component breakdowns are saved in valuation payloads; the UI's existing daily
  P&L columns and the new component inspector consume the result.
- Position inspector exposes native/base values, unrealised price/FX components,
  signed NAV/sector weights, beta contribution, daily components, sources and lots.
  Reads are pinned to the parent accounting run; older snapshots explicitly lack detail.
  New screenshots: docs/25k/position-value-390.png, position-daily-390.png and
  position-sources-1440.png. All five required widths passed browser checks.
- Backup-copy knk-nav-4.6 NAV remains SGD 70,597.57 with all original hashes retained;
  preservation report logs/sprint-nav-statement-preservation.json (28 copy valuation runs).
- Portfolio directory creates actual internal ledgers with explicit opening deposits,
  lists persisted accounts, and scopes accounting, entry and correction actions by ID.
  Creation uses configured currencies/securities and the current server UTC date boundary.
  Selecting a directory ledger does not change the main dashboard's KNK_MAIN context.
  Desktop/mobile evidence: docs/25k/portfolio-directory-1440.png,
  portfolio-create-390.png and portfolio-created-390.png.
- Corrections now share source-entry driver bounds, including derived base-value limits.
  Changed FX is marked AUDITED MANUAL CORRECTION while original provider evidence
  remains in before-history; voided records display their last corrected values and
  remain excluded from cash replay. Twelve regression tests cover these boundaries.
- Grouped exposures retain missing marks, exact signed net/gross and component
  values. Economic cash and outstanding manual balances are included once in
  currency/asset-class groups. Freshness includes stale cash FX and balance marks.
  Saved-run Exposures controls show groups, freshness and balance provenance;
  legacy snapshots explicitly lack unrecorded fields. New screenshot evidence:
  docs/25k/exposure-currency-1440.png, exposure-currency-390.png and exposure-freshness-390.png.
- Broker presentation now uses permitted metadata instead of copying internal
  financial fields. Historical valuation cache identity no longer changes every
  wall-clock minute; current-day freshness and source-change invalidation remain.
- Saved NAV now separates positive cash by currency, cash overdrafts, long assets
  and short liabilities. Settlement and recorded balance buckets appear once.
  Unknown marks produce INCOMPLETE, not zero liabilities. Legacy runs are not repriced.
- Shared decimal.js display formatting preserves decimal strings and bigint inputs,
  uses half-even rounding and bounds extreme inputs. Existing numeric source fields
  cannot regain precision already lost upstream; backend Decimal precision is not unlimited.
- Next implementation: remaining precision/persistence contracts and M2 performance
  and attribution, including incomplete-data states and explicit fee/date conventions.
- M2-M20, all category LOC floors and all final acceptance gates remain incomplete.

Progress/evidence: docs/LOC_EVIDENCE_25K.md, docs/BUILD_EVIDENCE_25K.md and
docs/ACCEPTANCE_25K.md. Do not infer completion from file existence.
