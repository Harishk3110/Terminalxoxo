# Portfolio-First Acceptance

Date: 2026-09-06. Baseline 6e707d3; see the release commit for delivered code.
This document distinguishes software verification from configured live services.
It does not certify the complete 80-step operating workflow.

## Accounting Evidence

KNK_MAIN opens with one explicit SGD 70,000 DEPOSIT on 2026-06-03.
Nine seeded entries include a recorded FX conversion, four purchases, one
partial sale, dividend and fee. The separate legacy book remains unchanged.

| Component | SGD |
| --- | ---: |
| Net contributed capital | 70,000.00 |
| Investment realised/unrealised P&L | 638.53 |
| Income | 13.43 |
| Fees | -41.16 |
| Cash FX P&L | -13.23 |
| Closing NAV | 70,597.57 |
| Cash | 23,476.64 |
| Securities | 47,120.93 |
| Reconciliation difference | 0.00 |

Displayed components are independently rounded; calculations use Decimal.
Market inputs end 2026-09-04 20:00 UTC and are DEMO DATA. They naturally become
stale after the configured threshold. No real-time or brokerage-return claim.

## Verification Gates

- 66 backend tests passed on a fresh isolated database in C:\Dev: ledger branches, balances, missing prices/FX, source
  preference and staleness, reset isolation, imported data/versions, curated
  fundamentals, factor statistics, execution approval, scope/revocation, raw
  storage retry, agent queue/archive/pause, portable seed entrypoint,
  deterministic correlation ordering/nulls and existing API workflows.
- API statement coverage 79%; accounting 92%, valuation 95%,
  price sources 96%, broker API 89%. This is not branch coverage or coverage of
  every UI action. Agent behavior is mocked, not a live TWS certification.
- Eight Vitest tests; typecheck/lint; no-execution application-source scan passed.
- Terminal/public production builds passed. Final fresh-database browser run:
  12 passed in 225.4 seconds, 33 screenshot comparisons without updating
  snapshots, no failures/skips/flaky tests. Desktop and mobile geometry/canvas
  checks and the file-approval/manual-ledger/review journeys passed.
- Isolated SQLite and PostgreSQL migration up/down/up passed. User database was backed up through
  SQLite's backup API before additive migration. Existing immutable records
  were hashed and retained across migration and API restart.
- Docker Compose configuration and Linux API image build passed. Container
  Alembic, idempotent seed and in-process API smoke passed against isolated
  PostgreSQL/Redis: all readiness checks ready, NAV 70,597.57, reconciliation 0.00.
  Thirteen additional focused tests passed with PostgreSQL configured: five API
  tests and eight SQLite-fixture tests. Full Compose/MinIO/worker/web health is
  not claimed. The test stack is separate from the working workstation database.
- Warm API medians in ms: summary 31.40, overview 29.84, forced NAV 450.63,
  cached risk 29.03. Cold summary 1053.94 ms. Six requests per endpoint, first excluded from warm median.
  File-preview latency and concurrent production load remain unmeasured.

## Acceptance Workflow Mapping

| Requested steps | Evidence and boundary |
| --- | --- |
| 1-2 Stack / login | API and isolated web run; existing auth tests retained. Docker API/PostgreSQL/Redis verified; full Compose stack not started. Local demo intentionally bypasses login. |
| 3-17 Portfolio | Browser overview/manual-entry/review journey; accounting/API tests cover cash, quantity, NAV, P&L, risk and audit records. |
| 18-22 Start/pair/watch folder | Scoped pairing API and vault selection tested; watcher detection/queue/pause/retry tested against mocked HTTP. A permanently running user-folder watcher is not configured. |
| 23-40 File operations | Browser upload/map/approve/catalogue journey plus CSV/XLSX/JSON, validation, immutable raw, version, dedup and archive unit tests. The actual Koyfin service is not connected. |
| 41-46 Portfolio price use | Approved AAPL fixture changes NAV source; missing preferred source and stale-file behavior tested. Mixed books are labelled MIXED SOURCES, not wholly FILE IMPORT. |
| 47-55 Quant backtest | Imported full-OHLC fixture runs through persisted queued/running/succeeded states with exact dataset version, results and equity curve. Close-only imports cannot supply invented OHLC. |
| 56-58 Factor | Momentum ranks, historical rank IC and quantiles computed; explicit purged IS/OOS split. Insufficient history remains unavailable. This is not statistical edge certification. |
| 59-61 Candidate | Pinned research-candidate create/review API and desk implemented. RESEARCH is supported; PAPER TESTING and automatic promotion are intentionally gated. No order sent. |
| 62-69 Risk/trade | Exposure/contribution/blotter desks, immutable stress jobs, manual hedge review and source scan. Not options repricing or a multi-asset optimizer. |
| 70-71 Reconciliation | Broker NAV/cash/quantity/cost/fill/commission comparisons and audited breaks tested with recorded mock snapshots; no live TWS comparison. |
| 72-78 Operations | Health probes, agent freshness, persisted file state history, API/DB/Redis/worker states. File parsing/import is synchronous; analytical jobs run in separate processes. |
| 79-80 Restart | Working API restarted; transaction/dataset/run/valuation hashes retained. Browser reload and imported-file/version persistence independently tested. No claim of full-stack crash recovery. |

## Operational Limits

Koyfin integration is permitted manually exported files with licence notes and
approved mappings, not direct API access or live data. XLS and ZIP are not
supported; XLSX uses the active sheet. Other reference imports do not silently
override positions. The agent is a command-line process, not a service installer.
Only mapped stock/ETF recorded broker fills enter the ledger. Broker current
account history does not automatically unlock internal performance metrics.

Automatic trusted-profile imports, editable profile versions, persistent factor
job history, verified strategy paper performance, PDF/deck output and production
multi-user hardening remain outstanding. These limitations are also recorded in
TASKS.md. No broker execution actions exist in application source.
