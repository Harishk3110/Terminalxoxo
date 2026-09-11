# Terminal Status

## Final Master Build, 2026-09-11

The 2026-09-11 master directive supersedes prior scope. Baseline `597f346` was
clean; recovery tag `pre-final-knk-terminal-build` is pushed. Current audit:
docs/FINAL_GAP_AUDIT.md. Final acceptance is not complete.

The final-build checkpoint implements encrypted TOTP enrollment/confirmation,
one-use recovery login, password changes and user-scoped session revocation.
Desktop/mobile security controls are operational. Trusted devices, production
provisioning and broader concurrency/security review remain open.

Docker Desktop 29.4.2 now runs PostgreSQL, Redis, MinIO, API, data/quant workers,
terminal, Prometheus and Grafana with healthy probes. Six migrations passed clean
SQLite and isolated PostgreSQL upgrade/downgrade/upgrade. The production frontend
image runs Next.js as a non-root user. The disabled report-engine is not running:
this is NOT an all-services or production-ready certification.

Local URL: http://127.0.0.1:3001/overview. It redirects anonymous visitors to the
styled setup/sign-in page. This is a separate Docker demo, not a migration of the
old SQLite installation. Its administrator has not been created. Existing `.env`,
`knk_terminal.db`, `.knk-object-store` and unrelated Docker volumes were preserved.
Keep Docker Desktop running. There is no verified public hosted URL.

Fresh verification:

- Backend: 923 passed, 13 warnings; 86.58% statement/line coverage. No branch
  coverage claim. Initial failed runs are retained in BUILD_EVIDENCE.md.
- Frontend: 235 terminal plus five shared unit tests passed; workspace TypeScript
  and lint passed. Node 22 production build passed both locally and in Docker.
- Four authentication modules passed scoped strict mypy; changed security,
  telemetry, bootstrap and migration modules passed scoped Ruff.
- Whole backend still fails: Ruff 218 errors; mypy 1,260 errors in 56 files.
- Full browser suite: 28/35 passed. A corrected explicit-date, run-ID-pinned
  multi-security backtest rerun passed. Six other failures remain: hedge, stress
  and four visual workflows dependent on those results. Old September demo data
  must not be relabelled fresh to conceal insufficient beta history.
- Live local setup page: HTTP 200, 45,884-byte CSS, 476 applied rules, no page errors
  or horizontal overflow at 1440px and 390px. Screenshots inspected.
- Prometheus API target is up; one Grafana dashboard is provisioned. Nine requested
  dashboards and managed PostgreSQL/object backup-restore are not complete.
- Meaningful LOC: 48,915 total, 35,642 source and 13,273 test lines. This is not a
  functional completion measure and is below the requested inventory target.

First unchecked task: replace disabled report-engine with authenticated,
source-pinned jobs on the existing SQL queue, then verify full Compose health.
See TASKS.md, docs/ACCOUNT_SECURITY.md, docs/LOCAL_DOCKER.md and BUILD_EVIDENCE.md.

Historical scope: PRD_TERMINAL_ONLY.md, 2026-09-07. The previous second-frontend
scope is cancelled. The 25K line-count target is not a completion certification.

## Current Verification, 2026-09-07

The following supersedes the historical checkpoints below. The requested nine
milestones are not all accepted: full workbook/deck/PDF packages, several advanced
domain workflows, backend strict typing and deployed-service checks remain open.
See TASKS.md, docs/REPORT_READINESS.md and docs/TERMINAL_ACCEPTANCE.md.

- Full backend sprint suite: 782 passed. Full API suite: 98 passed.
- Frontend unit suite: 232 passed; shared packages: five passed.
- Node 22 / Next.js 15.5.24 production build, workspace lint and TypeScript passed.
- New/changed standalone operations modules passed scoped Ruff. Whole-backend
  strict mypy failed with 1,264 errors in 57 files; these include new code.
- Browser regression passed 33/34 after the full-workspace bookmark fix and stale
  NAV-version, heading and chart assertions were corrected. The remaining quant
  fixture omitted a start date and correctly failed prior-FX validation. Its
  explicit-date saved-backtest alpha/Monte Carlo rerun passed. Screenshot review
  then caught oversized alpha result copies in workspace state. The saved-run
  reference/migration fix passed unit tests and a subsequent four-test browser run
  covering alpha save/reload/model/MC, hedge persistence and private-route access.
  All 34 distinct browser workflows passed across the full run and targeted reruns;
  this is not represented as a single zero-failure full-suite invocation.
- Subsequent backup/authentication/queue selection: 21 passed, including four
  added Windows reserved-device path cases. The original archive reverified.
- API 8000 was restarted with the current backend. Readiness returned HTTP 200;
  anonymous investment APIs returned 401. Both SQL queue dispatcher heartbeats
  were observed RUNNING. Redis, the local file agent and IBKR remain offline.
- Database/object backup verified, isolated restore verified, ten business-table
  snapshots preserved across restart, including three investment theses.
- On the subsequent launch request, the existing OPEN-KNK-TERMINAL.cmd started
  successfully in the background on port 3001. API and frontend probes responded.
  http://127.0.0.1:3001/overview redirects unauthenticated users to /login, which
  returned HTTP 200 with stylesheet references. This is a local, not hosted, URL.
- Docker Linux daemon is unavailable; Compose also requires an unset database
  password. Vercel authentication/deployment is not
  configured. No public hosted URL or all-services-healthy claim is made.

Pine v6 generation and CSV signal comparison are saved, hash-pinned and tested.
TradingView compilation remains UNVERIFIED; matching direction signals is not
fill/P&L equivalence. Existing private XLSX exports received contract-multiplier,
source-quality, column-alignment and download-integrity fixes, but are not the
requested complete reporting packages. The standalone unauthenticated hardcoded
report renderer is disabled and its Compose readiness check reflects that.

## Verified Terminal-only Checkpoint

Recovery tag pre-terminal-only-cleanup is pushed. All visitor-app source is removed.
One workspace frontend remains. Private root redirects to /overview; unauthenticated
requests redirect to /login. The API requires sessions even for local demo and
legacy /api investment aliases. Noindex and no-store are enabled.

Next.js 15.5.24 production build on Node 22: passed. Workspace lint passed.
31 existing API integration tests passed after authenticating their test clients.
27 access tests passed, including legacy-alias rejection.
Two browser checks passed: unauthenticated root/privacy and retired routes/noindex.

Port 3000 was stopped. The old ignored app build/cache directory could not be
removed because recursive deletion was policy-blocked. Source is absent from the
active Git tree; physical directory absence is NOT claimed.
The private 3001 launch was blocked at this earlier checkpoint; the later
successful local launch is recorded in Current Verification above.
API 8000 was restarted: health returned 200; anonymous current and legacy
portfolio endpoints returned 401. The real database remains in place.

## Continuing Work

Data checkpoint: 740 sprint tests, 98 API tests, 231 frontend tests and five shared
package tests passed. Subsequent provider/FRED selection passed 18 tests including
storage rollback. The Koyfin file/import/revalue/review browser workflow passed.
Connection persistence passed after correcting a delayed checkbox state; desktop/
mobile screenshots were inspected. Node 22 builds and broker-action scan passed.
Dedicated live vendors, SEC history/financial curation and separate FX precedence
remain unverified or incomplete as documented in PROVIDER_CONNECTIONS.md.
No user-facing 3001 deployment is claimed by these isolated browser tests.

Options checkpoint: 23 focused pricing/analytics/API/import tests passed. Node 22
production build and new-module Ruff passed. Browser synthetic-chain/GEX-sign/
Greek/IV/payoff/save-refresh checks passed, including unchanged ledger transactions
and NAV. Canvas pixel checks and inspected 1440px/390px screenshots passed.
European BSM, provider-unit requirements, expiry-time convention, missing-chain
states and selected-underlying limits are explicit in OPTIONS_DATA.md and
GAMMA_GEX_METHODOLOGY.md. No real options provider or broker execution is connected.

The guarded SGD 100,000 demo correction is applied and its SQLite backup verified.
Original 16 transactions, 9 transaction details, 23 valuation runs and 1 analysis
run are unchanged. NAV at the coherent demo close is SGD 100,597.57, BALANCED.
Exact Decimal valuation curves now feed the interactive performance workspace.
83 focused accounting/performance tests and 231 frontend tests passed. Six
performance-domain files passed strict mypy. The broader sprint run passed 595
and exposed one stale anonymous-actor assertion; all 30 context tests passed after
fixing that assertion. The API suite passed 93 and exposed one direct-call test
requiring authentication; all five broker-agent tests passed after correction.
Three operating browser checks passed, followed by three performance/privacy
checks after visual fixes. Desktop/mobile screenshots were inspected; percentage
formatting and mobile toolbar overlap were corrected. Node 22 build passed.

NAV, lots, corrections, cash, imports, research and saved analysis
engines are retained. Their complete new acceptance workflow is not yet certified.

Risk checkpoint: 625 sprint tests, 95 API tests and 231 frontend tests passed.
Historical/parametric/Monte Carlo/EWMA risk, audited limits and saved manual hedge
analysis are connected. Stress factor/cash/balance attribution reconciles, and
unsupported VIX mapping returns unavailable rather than zero. A subsequent
eight-test broker/limit selection verified amended and voided fill reconciliation.
The saved limit/model/hedge browser workflow passed; screenshot review prompted
mobile panel-height and input-persistence fixes. Both the final responsive hedge
workflow and persisted stress/export check then passed against a fresh production
build. Screenshots were inspected at 1440px and 390px.
The local 8000 process has not been restarted with these code changes; isolated
test servers are not evidence that the user's 3001 terminal is running.

Whole-backend lint/type failures from the earlier baseline remain disclosed.
Quant checkpoint: 665 sprint tests, 97 full API tests and 231 frontend tests passed.
Subsequent focused runs passed 28 factor/input/cap tests and nine alpha/review tests.
Node 22 production builds passed; new quant modules passed Ruff and the broker-
action scan passed. The first browser run found a virtualised-row test assumption
and screenshot review exposed flex-shrunk panels. Scoped scrolling/dimensions fixed
the overlaps. Both final browser workflows passed: saved alpha/model/artifact/MC/
factor checks and multi-security SGD backtests with pinned FX, costs and fills.
1440px/390px screenshots were inspected. Corporate-action backtests, point-in-time
fundamental factors, full attribution and general strategy walk-forward optimisation
remain explicitly incomplete. No live user-facing 3001 deployment is claimed.
Docker Linux daemon was unavailable; Vercel CLI was logged out; no cloud URL is
verified. Existing local data and historical runs are retained.

Equity checkpoint: 693 sprint tests, 97 full API tests and 231 frontend tests
passed. Subsequent focused runs passed 17 equity tests and all 10 file-import/
operations tests, including partial restatement provenance and unit rejection.
The new test insertion initially misplaced an existing factor assertion; it was
restored to its original test and the file rerun passed. Node 22 production build,
new-module Ruff and broker-action scan passed. Both browser workflows passed,
then both passed again after denser two-column desktop DCF and mobile rechecks.
Saved FIN/FCFF/WACC/comparables/thesis workflows and interactive price charts are
connected. Thesis versions preserve manual-ledger references and history.
Segments, ROIC, historical/forward valuation multiples and unconnected provider
workflows remain unavailable; see EQUITY_RESEARCH.md. No 3001 deployment claimed.
