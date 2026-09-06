# STATUS 25K

Sprint active. Baseline: c3d9e847604fbbfb59df170c1b5f83f7dbec94a1.
Initial verified checkpoint: e25b94e52a7669458beaaa8c7685942dc256cd55, pushed to origin/main.
Storage-boundary checkpoint: e5f5d43282d1f6f63c22e0eeec954155ee634eaf, pushed.
Current change: transaction provenance and entry/detail workflows; `git rev-parse HEAD` resolves this checkout.
Branch main; existing origin retained. No sprint milestone is certified complete.

- Current milestone: M1 in progress, audited ledger and accounting subledgers implemented.
- Qualifying delta at 2026-09-06 12:15 UTC: 6,275 conservative novel source/test lines.
  Backend 1,908; frontend 1,222; workers/agents/reports/infra 263; tests 2,882.
  This is an interim worktree count, not a milestone certification.
- Gates: backend 9,000; frontend 6,000; infrastructure/agents/reports 3,000;
  substantive tests 7,000; total 25,000.
- Services: prior local API PID 30820 on 127.0.0.1:8000 still serves baseline code.
  Readiness reports API/database ready, Redis TimeoutError and local object storage ready.
  No listener on 3001. Isolated Playwright servers on 8001/3002 stopped after tests.
- Operational routes/APIs: portfolio resources added, including append-only
  corrections, scoped lot details, accounting policy, cash, recalculation,
  historical-run accounting components and append-only balance adjustments.
- Tests: combined Python suite 442 passed, including all 66 existing backend tests;
  targeted accounting coverage 98% (1,194 statements, 24 missing), not whole-app coverage.
  Frontend 103 passed; production build/typecheck passed (96.1 kB terminal route).
  Repository test-unit command also passes five shared-package tests; other package echo scripts are not tests.
  Full Playwright suite 18 passed on the final frontend (run sprint25k-entry-2).
  Legacy-reference read hardening is separately covered by the final Python run.
- New Python modules: Ruff and strict mypy passed on 22 source files (legacy imports silent).
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
- First unchecked execution task: finish M1 input/storage precision contracts,
  position/attribution edge cases and portfolio creation UI. Audit timestamps are
  provenance only; same-day replay order remains the original ledger record order.
  Audit references are not yet editable through the correction dialog.
  Live additive migration, permitted service deployment and M1 certification remain.
- Existing storage contract is now explicit: inputs and derived gross must fit eight
  decimals; provider FX rounding is recorded, and unsafe SQLite round-trips are rejected.
  This is a safety boundary, not expanded precision support or a production DB certification.
- Next command: `rg -n 'daily_contributions|last_positions|risk_contribution|sector' services/api/app/portfolio_valuation.py`.
- M2-M20, all category LOC floors and all final acceptance gates remain incomplete.

Progress/evidence: docs/LOC_EVIDENCE_25K.md, docs/BUILD_EVIDENCE_25K.md and
docs/ACCEPTANCE_25K.md. Do not infer completion from file existence.
