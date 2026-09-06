# STATUS 25K

Sprint active. Baseline/current commit: c3d9e847604fbbfb59df170c1b5f83f7dbec94a1.
Branch main; existing origin retained. No sprint milestone is certified complete.

- Current milestone: M1 in progress, audited ledger and accounting subledgers implemented.
- Qualifying delta at 2026-09-06 11:22 UTC: 4,940 conservative novel source/test lines.
  Backend 1,723; frontend 790; workers/agents/reports/infra 263; tests 2,164.
  This is an interim worktree count, not a milestone certification.
- Gates: backend 9,000; frontend 6,000; infrastructure/agents/reports 3,000;
  substantive tests 7,000; total 25,000.
- Services: prior local API PID 30820 on 127.0.0.1:8000 still serves baseline code.
  Readiness reports API/database ready, Redis TimeoutError and local object storage ready.
  No listener on 3001. Isolated Playwright servers on 8001/3002 stopped after tests.
- Operational routes/APIs: portfolio resources added, including append-only
  corrections, scoped lot details, accounting policy, cash, recalculation,
  historical-run accounting components and append-only balance adjustments.
- Tests: combined Python suite 369 passed, including all 66 existing backend tests;
  targeted accounting coverage 98% (1,069 statements, 23 missing), not whole-app coverage.
  Frontend 52 passed; production build/typecheck passed. Full Playwright suite 16 passed;
  four ledger workflows rerun successfully after mobile header fix, at five viewports.
- New Python modules: Ruff and strict mypy passed on 19 source files (legacy imports silent).
- Migrations 0004/0005 passed 15 lifecycle/schema/constraint tests. A fresh saved-data
  backup copy upgraded from 0003 to 0005, valued at SGD 70,597.57, and retained all
  captured original hashes (16 transactions, two dataset versions, 22 prior runs).
  The user's real knk_terminal.db has NOT been migrated; no live deployment is claimed.
- Frontend: Home accounting dialog and Trade Monitor corrections integrated;
  Activity and Balances now expose persisted components and audited adjustments.
  Desktop/mobile screenshots: docs/25k/activity-1440.png and activity-390.png.
- Docker: daemon 29.4.2 responds; docker ps lists no running containers.
  This is not complete-stack health. User-facing web launch was denied earlier;
  no alternative server launch was used to bypass that denial.
- Blockers: none for demo/domain/contract implementation. Live credentials absent
  are not treated as blockers.
- First unchecked execution task: finish M1 transaction audit fields, input/storage
  precision contracts, complete position/attribution edge cases and creation/action UI.
  Live additive migration, permitted service deployment and M1 certification remain.
- Next command: `rg -n 'LedgerRequest|execution_id|trade_timestamp|gross_amount|net_amount' services/api/app/portfolio_api.py services/api/app/models.py services/api/app/portfolio_operations.py services/api/app/ledger_revisions.py`.
- M2-M20, all category LOC floors and all final acceptance gates remain incomplete.

Progress/evidence: docs/LOC_EVIDENCE_25K.md, docs/BUILD_EVIDENCE_25K.md and
docs/ACCEPTANCE_25K.md. Do not infer completion from file existence.
