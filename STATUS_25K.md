# STATUS 25K

Sprint active. Baseline: c3d9e847604fbbfb59df170c1b5f83f7dbec94a1.
Initial verified checkpoint: e25b94e52a7669458beaaa8c7685942dc256cd55, pushed to origin/main.
Storage-boundary checkpoint: e5f5d43282d1f6f63c22e0eeec954155ee634eaf, pushed.
Transaction-entry checkpoint: c770947a04b3b169332f0ff6442780b5db06d99a, pushed.
Position-period checkpoint: bef7c5cc84b8efbbc61382ca3adc0f8d96d2135f, pushed.
Position-inspector checkpoint: 8ac83a42153845dd9cc6c2b190d165355761180f, pushed.
Portfolio-directory checkpoint: bb8812fd99420534498ac62af36764cafb97f35f, pushed.
Correction-storage checkpoint: 1318447728acfac59058bb3e444b3521c86f68a8, pushed.
Current change: grouped exposure/freshness, broker boundary and historical cache; `git rev-parse HEAD` resolves this checkout.
Branch main; existing origin retained. No sprint milestone is certified complete.

- Current milestone: M1 in progress, audited ledger and accounting subledgers implemented.
- Qualifying delta at 2026-09-06 13:45 UTC: 9,357 conservative novel source/test lines.
  Backend 2,436; frontend 2,004; workers/agents/reports/infra 263; tests 4,654.
  This is an interim worktree count, not a milestone certification.
- Gates: backend 9,000; frontend 6,000; infrastructure/agents/reports 3,000;
  substantive tests 7,000; total 25,000.
- Services: prior local API PID 30820 on 127.0.0.1:8000 still serves baseline code.
  Readiness reports API/database ready, Redis TimeoutError and local object storage ready.
  No listener on 3001. Isolated Playwright servers on 8001/3002 stopped after tests.
- Operational routes/APIs: portfolio resources added, including append-only
  corrections, scoped lot details, accounting policy, cash, recalculation,
  historical-run accounting components and append-only balance adjustments.
- Tests: combined Python suite 571 passed, including all 66 existing backend tests;
  targeted accounting coverage 98% (1,558 statements, 26 missing), not whole-app coverage.
  Frontend 143 passed; production build/typecheck passed (102 kB terminal route).
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
- First unchecked execution task: finish M1 derived-storage and display precision,
  NAV balance-sheet and remaining persisted metric contracts. Audit timestamps are
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
- Backup-copy knk-nav-4.5 NAV remains SGD 70,597.57 with all original hashes retained;
  preservation report logs/sprint-exposure-preservation.json (27 copy valuation runs).
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
- Next implementation: explicit NAV short/overdraft liability components and
  remaining precision/persistence work, then M2 performance and attribution.
- M2-M20, all category LOC floors and all final acceptance gates remain incomplete.

Progress/evidence: docs/LOC_EVIDENCE_25K.md, docs/BUILD_EVIDENCE_25K.md and
docs/ACCEPTANCE_25K.md. Do not infer completion from file existence.
