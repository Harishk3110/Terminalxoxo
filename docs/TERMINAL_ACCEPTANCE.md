# Terminal Acceptance

This document records measured checks, not a claim that all nine milestones pass.

## Terminal-only Checkpoint

- Recovery tag created and pushed before source removal.
- One active frontend; visitor route/source/package/service removed.
- Production frontend build passed on Node 22 / Next.js 15.5.24.
- Workspace lint passed.
- Existing authenticated API integration selection: 31 passed.
- Authentication regression selection including legacy aliases: 27 passed.
- Browser private-root/retired-route checks: two passed.
- Noindex, no-store, opaque HTTP-only sessions, expiry and logout rejection tested.

## Not Yet Accepted

Physical removal of ignored retired-app build/dependency artifacts was blocked.
The main 3001 process is not claimed running merely because the isolated browser
harness passes on 3002. Full Docker health and hosted deployment are unverified.
The cross-desk acceptance workflows are still in progress.

## Capital and Performance Checkpoint

- Guarded opening-capital amendment applied to the local managed demo, with SQLite backup and canonical-table hash preservation.
- Closing demo NAV SGD 100,597.57; opening contribution SGD 100,000; balance reconciliation BALANCED.
- 83 focused accounting/performance tests passed; 231 frontend tests passed.
- Broader sprint run: 595 passed, one outdated actor assertion corrected; its 30-test file then passed.
- API run: 93 passed, one direct-call authentication test corrected; its five-test file then passed.
- Strict mypy passed all six performance-domain files.
- Three operating browser checks passed: responsive populated Overview/charts, file-price import and manual ledger review, and saved performance.
- Three subsequent checks passed after screenshot-driven fixes: numeric performance rendering/mobile control geometry, private root, retired routes/noindex.
- Production build passed on Node 22 / Next.js 15.5.24. No public route was statically generated. Broker-action source scan passed.

The original user acceptance spans manual BUY -> cash/positions/NAV/performance/
risk/audit updates, persisted backtests and research, gamma/GEX, imported Koyfin
price fallback, restart persistence and final tests. These must be verified against
the actual engines; navigation or a screenshot alone does not certify them.
