# Final Master Build Tasks

Controlling directive: 2026-09-11 final master build. Baseline `597f346`.
Historical completed work below is preserved, not equivalent to final acceptance.

- [x] M0: inspect baseline, push pre-final-knk-terminal-build tag and record FINAL_GAP_AUDIT.
- [x] M0: verify current terminal build and meaningful categorized LOC report (71 counter tests; Next production build passed).
- [x] M1: preserve local configuration/data and start PostgreSQL, Redis, MinIO, API, data/quant workers, terminal and monitoring with real health checks.
- [x] M1: complete TOTP enrollment/recovery/password/session security workflows; focused API, UI and browser tests pass.
- [ ] M1: replace disabled report-engine with authenticated source-pinned jobs on the existing SQL queue; then verify full Compose health including reports.
- [ ] M1: complete trusted-device lifecycle, production provisioning/key operations and broader security/concurrency review.
- [ ] M2: complete security-master lifecycle, immutable remote storage and source conflict policies.
- [ ] M3: rerun full 100K ledger/NAV/corporate-action/FX and restart acceptance without resetting user data.
- [ ] M4: complete alpha attribution and certify performance coverage.
- [ ] M5: complete liquidity/derivatives risk and full before/after trade reconciliation.
- [ ] M6: complete nonlinear stress and constrained manual rebalance.
- [ ] M7: certify local-agent and Data Drop full acceptance with preserved Parquet lineage.
- [ ] M8: finish provider adapters, SEC curation/revisions, FX/news/AI contract tests.
- [ ] M9: finish corporate-action backtests, strategy walk-forward, fundamental factors and quant sandbox.
- [ ] M10: finish equity segments/ROIC/historical valuation/estimates/earnings.
- [ ] M11: finish multi-expiry payoff, full portfolio Greeks and supported options history.
- [ ] M12: finish isolated report workbooks/decks/PDF and Pine acceptance.
- [ ] M13: verify complete registry, linked desks, source/timestamp/loading/error states.
- [ ] M14: resolve six remaining stress/hedge/dependent visual failures with explicit dated inputs and separate error-state tests; do not fabricate beta history or relabel stale data.
- [ ] M14: full lint/types/coverage, visual/performance, PostgreSQL backup/restore and deployment gates.
- [ ] M15: pass every applicable step in docs/FINAL_ACCEPTANCE.md, commit and push.

## Previous Terminal-only Checkpoints

Recovery tag: pre-terminal-only-cleanup. Milestones follow the user's priority order.

- [x] Push recovery tag before removal.
- [x] Remove visitor-app tracked source, routes, service and workspace membership.
- [x] Keep apps/terminal-web as the sole frontend.
- [x] Require server-validated sessions before rendering investment pages.
- [x] Require API authentication in local demo and production.
- [x] Disable indexing and test root/login/retired routes.
- [ ] Remove ignored retired-app directory on disk (execution-policy restriction).
- [x] Complete SGD 100,000 audited demo correction and verify data preservation.
- [x] Verify portfolio/NAV/position/performance resources and manual BUY through cash, NAV, risk, trade review and audit.
- [x] Verify current-weight risk, audited limits, trade/reconciliation, linear/correlation stress and saved manual hedge workflows.
- [ ] Extend risk with measured duration, option repricing and futures/FX covariance where supported input data exist.
- [x] Verify saved alpha, technical factors, offline multi-security backtests, model/expanding-window evaluation, Monte Carlo and candidate review records.
- [ ] Complete corporate-action/weekly/intraday backtests, point-in-time fundamental factors, detailed alpha attribution and general strategy walk-forward optimisation.
- [x] Verify annual/quarterly/TTM, saved FCFF/WACC/comparables, structured theses and security views.
- [ ] Complete verified segments, ROIC, historical/forward multiples and provider-driven earnings/ownership/short-interest/events.
- [x] Verify imported/synthetic chains, Greeks, GEX/DEX, observed IV, saved analyses and hypothetical payoff without ledger mutation.
- [ ] Extend options beyond European pricing and selected-underlying positions; historical OI flow/cones require datasets.
- [x] Verify Data Drop formats, Koyfin approval/revaluation, private attachments, provider controls and SEC/OpenFIGI/JSON adapter tests.
- [ ] Verify licensed live vendors, full SEC history/curation, separate FX priority and remaining specialized data adapters.
- [x] Implement saved Pine v6 templates and user-export direction comparison with honest compilation limits.
- [x] Fix existing report source metadata, column alignment and contract multiplier formulas.
- [ ] Complete model XLSX/decks/PDF outputs (alternate-engine permission granted by final master directive; implementation remains open).
- [x] Replace synthetic daemon completion with atomically claimed analytical/provider queues and expiring heartbeats.
- [x] Verify local database/object backup and isolated non-overwriting restore.
- [x] Add persisted login throttles, origin checks and per-user all-session revocation.
- [x] Complete backend/frontend regression and all 34 browser workflows across full/targeted runs, including workspace reload fixes.
- [x] Start the existing local terminal launcher and verify the main route and login response on port 3001.
- [ ] Resolve whole-backend strict typing and remaining deployed operations (Docker credentials/daemon, live providers and production controls).

No provider-dependent or incomplete function may be marked AVAILABLE.
No broker execution capability is permitted.
