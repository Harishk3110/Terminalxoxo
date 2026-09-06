# Terminal-only Tasks

Recovery tag: pre-terminal-only-cleanup. Milestones follow the user's priority order.

- [x] Push recovery tag before removal.
- [x] Remove visitor-app tracked source, routes, service and workspace membership.
- [x] Keep apps/terminal-web as the sole frontend.
- [x] Require server-validated sessions before rendering investment pages.
- [x] Require API authentication in local demo and production.
- [x] Disable indexing and test root/login/retired routes.
- [ ] Remove ignored retired-app directory on disk (execution-policy restriction).
- [x] Complete SGD 100,000 audited demo correction and verify data preservation.
- [ ] Complete portfolio/NAV/position/performance acceptance workflows.
- [x] Verify current-weight risk, audited limits, trade/reconciliation, linear/correlation stress and saved manual hedge workflows.
- [ ] Extend risk with measured duration, option repricing and futures/FX covariance where supported input data exist.
- [ ] Complete quant/factor/alpha/model/walk-forward acceptance.
- [ ] Complete equity/DCF/comparables/thesis acceptance.
- [ ] Complete options-chain/Greeks/gamma/GEX acceptance.
- [ ] Complete provider/file-source/freshness acceptance.
- [ ] Complete internal Excel/decks/PDF/Pine acceptance.
- [ ] Verify all operations components and final regression suite.

No provider-dependent or incomplete function may be marked AVAILABLE.
No broker execution capability is permitted.
