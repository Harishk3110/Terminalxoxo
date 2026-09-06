# STATUS

Date: 2026-09-06
Product: KnK Capital Terminal / KnK Capital
Repository: https://github.com/Harishk3110/Terminalxoxo
Branch: main. Portfolio-first baseline: 6e707d3.

## Delivery

The approved dense black/amber shell now opens on the Portfolio Command Centre.
KNK_MAIN is a separate, auditable SGD 70,000 demonstration ledger. The legacy
reference book, users, datasets and runs are preserved.

- Decimal, native-currency ledger with 17 transaction types and full NAV buckets.
- Immutable valuations, source provenance, flow-adjusted P&L, TWR/XIRR and risk.
- Thirteen-metric ribbon and seven overview panels; seven operating desks.
- Trade events/reviews, pre/post risk snapshots, reconciliation and manual hedges.
- CSV/XLSX/JSON Data Drop, 12 profiles, approval, hash deduplication and lineage.
- Outbound Windows-vault file agent and optional scoped read-only paper reader.
- Equity coverage/imported statements, Quant monitor, pinned backtests, measured
  factor IC/quantiles and research-only candidate records.
- 110 canonical functions; workbook exports; actual service/agent freshness.
- Migration 0003 adds 19 accounting, source, ingestion and agent tables.

## Verification

- Backend: 66 passed on a fresh isolated database in C:\Dev; three framework deprecation warnings.
- API statement coverage 79%; accounting 92%, valuation 95%, source resolver 96%, broker API 89%.
- Vitest: 8 passed. No-execution source scan passed.
- Monorepo typecheck and lint passed.
- Terminal production build passed: logs/dev-portfolio-release, 180 kB first load.
- Public production build passed: logs/public-dev-release, 94 kB first load.
- Browser: 12 passed in 225.4 seconds; 33 screenshot comparisons without updating
  snapshots, four desktop sizes plus mobile; no failures, skips or flaky tests.
- Fresh SQLite and isolated PostgreSQL migration upgrade / downgrade to 0002 / upgrade passed.
- User SQLite backup, additive migration and immutable-record preservation passed.
- Local API restart and persisted-record checks completed.
- Docker Linux API image built; container Alembic and idempotent seed passed.
  Container API readiness reported API, PostgreSQL, Redis and local object storage
  ready; portfolio NAV/reconciliation matched SQLite. Thirteen focused tests
  passed with PostgreSQL configured (five API tests; eight isolated SQLite fixtures).
  Full Compose stack, MinIO, distributed workers and web containers remain unverified.

## Valuation and Timing

Local DEMO DATA as of 2026-09-04 20:00 UTC: NAV SGD 70,597.57, cash 23,476.64,
securities 47,120.93, P&L 597.57, reconciliation difference 0.00.
These are deterministic demonstration results, not real-time investment returns.

Measured five-sample warm medians in C:\Dev: summary 31.40 ms, overview API 29.84 ms,
NAV recalculation 450.63 ms, cached risk 29.03 ms. Cold summary was 1053.94 ms.
Local measurements are not load-test guarantees. File-preview latency has not
been separately benchmarked.

## Remaining Limits

Real TWS/paper connectivity, live provider data and credentials remain unverified.
Broker current NAV never inherits demo historical risk/performance. Optional
automatic file-profile approval, profile editor, agent installer/service,
PDF/decks, arbitrary strategy execution, walk-forward optimization and verified
paper-strategy returns are not implemented. Candidates cannot claim an edge or
promote themselves to paper trading. Imported positions remain references.

Risk excludes cash-FX and liability sensitivities; stress explicitly includes
USD cash FX. Historical NAV restates accepted data, not point-in-time versions.
Production multi-user authorization, distributed supervision and specialist
provider-required functions remain outside this local workstation release.
The complete 80-step acceptance workflow is not claimed: see
docs/PORTFOLIO_ACCEPTANCE.md for implemented, tested and unverified boundaries.

## Runtime

API: http://127.0.0.1:8000, migrated and restarted with portfolio-first code.
Working project moved to C:\Dev. Git history was restored from origin/main
without replacing the transferred worktree. Immutable record hashes match the
old folder; dependencies were reinstalled because copied package links retained
OneDrive paths. The API now runs from C:\Dev, not the old OneDrive directory.
Web: the session policy blocked launching the user's port 3001. The verified
build is available through OPEN-KNK-TERMINAL.cmd after the API is running.
Main page: http://127.0.0.1:3001/overview. This is local, not a public deployment.
The isolated browser tests use ports 8001/3002 and separate SQLite/object stores.

API/SQLite/local object storage healthy; Redis OFFLINE; on-demand workers IDLE;
file agent and IBKR OFFLINE; FRED DEMO. Other unprobed services remain NOT_VERIFIED.
