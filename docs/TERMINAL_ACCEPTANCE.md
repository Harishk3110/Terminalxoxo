# Terminal Acceptance

## Current Final-Operations Checkpoint

2026-09-07: this is measured implementation/verification evidence, not acceptance
of every requested feature. Historical checkpoint counts below are not additive.

| Check | Result |
| --- | --- |
| Full backend sprint tests | 782 passed, 11 warnings |
| Full authenticated API tests | 98 passed, 3 warnings |
| Frontend unit tests | 232 passed |
| Shared-package tests | 5 passed |
| Node 22 production build | Passed, Next.js 15.5.24 |
| Workspace lint / TypeScript | Passed |
| New standalone operations/report/Pine module Ruff | Passed |
| Whole-backend strict mypy | Failed: 1,264 errors in 57 files, including new code |
| Chromium regression | 34 distinct workflows passed across full/targeted runs; final four-test workspace/privacy rerun passed |
| Local API readiness / private endpoint | HTTP 200 / anonymous HTTP 401 |
| Data / quant dispatchers | Fresh RUNNING heartbeats observed |
| SQLite plus object backup / isolated restore | Verified, no active data overwritten |
| Ten business-table restart snapshots | Preserved, including ledger, analyses and theses |
| User-facing frontend 3001 | Existing launcher started; /overview redirects to /login, HTTP 200 with stylesheet references |
| Docker Linux daemon / Compose | Unavailable / required database password unset |
| Hosted deployment | Not performed; authentication unavailable |

The first full Chromium run passed 24/34. Failures exposed three stale NAV-engine
version checks, an old connection heading, four old hedge-chart assumptions,
an alpha test that incorrectly assumed weekday-eligible mutated portfolio returns,
and a genuine full-workspace bookmark bug. New route activation now retains at most
20 tabs; the regression starts from 20 tabs and verifies saved hedge inputs after
reload. Alpha uses a pinned, completed DEMO_RESEARCH backtest. Domain validation
of nonzero weekend portfolio returns is unchanged.

The second full run passed 33/34, including all four desktop visual workspaces and
mobile bounds/pixel checks. Its new alpha fixture omitted a start date, so it was
correctly rejected for missing prior FX on the earliest demo bar. It now specifies
2025-01-01 and uses the same saved net backtest for Monte Carlo. The corrected
workflow passed. Screenshot inspection nevertheless exposed an oversized workspace
configuration: alpha results were copied into the settings even though a saved
analysis already existed. The UI now persists only the run ID, refetches its saved
result on reload and migrates legacy copies without losing controls. A unit test
checks the migration; the new browser check requires a successful workspace POST
and restored coefficients after reload. The full-run JSON is retained locally in
`logs/terminal-final-m9-r2-results.json`; private test artifacts are not committed.
The subsequent four-test run passed alpha save/reload/model/Monte Carlo, full-tab
hedge persistence, private root and retired routes. Its record is
`logs/terminal-workspace-m9-r4-results.json`. Updated desktop/mobile images were
inspected and the workspace-save warning was absent. All 34 distinct browser
workflows have passing evidence, but no single zero-failure full-suite invocation
is claimed. The latest frontend production build and lint passed.

A later 21-test backup/authentication/queue selection passed after adding four
Windows device-path rejection cases. The actual 317-file backup was reverified
with the unchanged archive SHA-256 recorded in OPERATIONS_VERIFICATION.md.
The final complete backend sprint rerun then passed all 782 tests; the frontend
unit rerun passed 232, including the new workspace migration test.

New checks cover manual BUY through cash/positions/NAV/performance/risk/trade
review/audit; per-user all-session revocation; origin rejection and persisted login
limits; reset rejection without deletion; duplicate queue claims and real probe
outcomes; expiring worker health; backup hashes, traversal rejection and isolated
restoration; Pine validation, source persistence and uploaded CSV comparison;
and legacy report metadata/column/multiplier contracts.

Pine browser generation/comparison and inspected 1440px/390px screenshots passed
in the initial full suite. TradingView compilation, independently verified price
data, fills and P&L equivalence remain unverified. Full formula-driven XLSX families,
IC PPTX/PDF/PNG packages are blocked by the unavailable artifact runtime; alternate
authoring-engine approval has not been received. Existing authenticated XLSX
exports are not certification of those report requirements.

Remaining advanced domain scope is listed in TASKS.md and the corresponding
methodology docs. Production TLS, credentials, edge controls, backup scheduling,
retention and encrypted remote copies are not established by these tests.

## Data Checkpoint

- 740 sprint, 98 API, 231 frontend and five shared-package tests passed.
- Focused provider/FRED rerun: 18 passed, including atomic storage-failure rollback.
- Koyfin CSV approval, source fallback, portfolio revalue and saved review browser
  workflow passed. Connection enable/revoke/refresh passed after a checkbox fix.
- Source/hash/PII isolation, failed requests, Parquet/XLS/JSONL, attachments and
  disabled FRED legacy ingestion have substantive tests.
- No live SEC/OpenFIGI/vendor connectivity was certified by mocked transports.
- New docs record file-agent settings, model limits and broker read-only boundaries.

## Options Checkpoint

- 23 focused tests passed: BSM reference/IV/advanced Greeks, GEX signs, quote
  exclusions, provider units, owned quantities, imports and source integrity.
- Production build and new-module Ruff passed.
- Browser chain/GEX/Greeks/IV/payoff/history workflow passed; ledger transactions
  and NAV were unchanged. Canvas pixels and desktop/mobile width were checked.
- 1440px/390px screenshots inspected. Production providers and complete multi-
  underlying portfolio derivatives risk are not certified by the synthetic fixture.

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
The main 3001 process was verified separately by HTTP after the user requested a
working local link. Full Docker health and hosted deployment remain unverified.
Advanced domain, complete reporting and deployed-service requirements remain
unaccepted as listed in TASKS.md; passing workflow tests do not complete that scope.

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

## Risk Checkpoint

- 625 sprint tests, 95 API tests and 231 frontend tests passed.
- Twenty subsequent risk/hedge/operations tests and eight broker/limit tests passed.
- Covariance/component reconciliation, seeded Monte Carlo, missing-data states,
  risk-limit persistence, amended fills, voids, ETF FX sizing and saved hedge inputs tested.
- Node 22 production build passed; forbidden broker-action source scan passed.
- Browser limit changes, model settings, hedge calculation, durable review and refresh passed.
- Screenshot review caught short mobile hedge panels; scoped height/persistence
  fixes passed the final browser rerun with geometry assertions at 1440px/390px.
- Both final browser checks passed: risk/model/hedge review and persisted stress/export.
- Statistical risk excludes cash-FX/liability/nonlinear option risk. VIX-to-option
  mapping, measured duration and futures/FX VaR remain unavailable, not simulated as live.

## Quant Checkpoint

- 665 sprint tests, 97 API tests and 231 frontend tests passed.
- Subsequent focused runs: 28 factor/input/cap tests and nine alpha/review tests passed.
- Node 22 production builds, new-module Ruff and broker-action scan passed.
- Model coefficient/feature causality, purged partitions, seed reproducibility,
  next-open fills, multi-security costs, covariance weighting, cash/sector caps,
  source hashes and prior-published FX tested.
- Browser model/artifact download, saved alpha, Monte Carlo and factor controls
  passed. Multi-security SGD backtests with saved gross/cost/FX evidence passed.
- Screenshot review found flex/grid overlap; scoped scroll and fixed-height plot
  tracks were added. Final model geometry checks and 1440px/390px images passed.
- The first factor browser assertion assumed SPY was in the rendered virtual
  window. The corrected assertion checks an actually visible factor row.
- Limits and pending workflows are explicit in QUANT_RESEARCH.md and
  ALPHA_METHODOLOGY.md. A positive demo result is not certified alpha or an edge.

## Equity Checkpoint

- 693 sprint, 97 API and 231 frontend tests passed.
- Subsequent 17 equity tests and 10 import/operations tests passed.
- FCFF, WACC, TTM completeness, unit rejection, restatements, source lineage,
  peer statistics, immutable thesis references and authentication tested.
- Node 22 production build, new-module Ruff and broker-action scan passed.
- Two browser workflows passed; both passed again after denser desktop layout.
- DCF/COMP/thesis save/revision/refresh and security chart controls tested.
- 1440px/390px screenshots inspected; chart/table geometry does not overlap.
- The isolated browser harness is not a live 3001 deployment. Provider-driven
  workflows and financial-model limits are recorded in EQUITY_RESEARCH.md.
