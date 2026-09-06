# Terminal Acceptance

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
