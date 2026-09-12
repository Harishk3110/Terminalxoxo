# Final Function Matrix

Starting application: 41baacb. This matrix is not a release pass. Existing route
and workflow details remain in OVERNIGHT_RC_FUNCTION_MATRIX.md and the acceptance
documents. Per-function closure must be reconciled with FINAL_CLOSURE_TASKS.md.

| Function Group | Verified boundary | Remaining final closure |
| --- | --- | --- |
| HOME / PORT / NAV / PNL / PERF | Internal ledger, saved valuations, private views, restart tests | Full accounting/attribution matrix |
| RECONCILIATION | Missing NAV remains missing; JSON-safe persisted breaks, strict saved comparison inputs, generic API rejection, unconnected desktop/mobile workflow | Live broker acceptance and complete release gates |
| TRADES / REVIEW | Typed recorded evidence, protected ledger/risk/review fields, missing-value honesty and desktop/mobile persisted review | Current full release and live broker acceptance |
| ALPHA / BETA / RISK / STRESS / HEDGE | Typed source-aware calculations, persisted runs, focused browser passes | Complete history, decomposition, cost/review acceptance |
| FIN / DCF / WACC / COMP / THESIS | Imported/demo receipts, exact parity, saved hashes, immutable versions; isolated FIN point and DCF desktop/mobile browser passes | Full release certification; preserve verified code |
| SEGMENTS / ROIC / HISTORICAL / FORWARD MULTIPLES | Explicit missing/unsupported labels | Implement required data models, PIT calculations and UI |
| BACKTEST / FACTOR / EDGE / MODEL / MC / WALK | Persisted asynchronous research and tested core engines | Corporate actions, PIT fundamentals, attribution, general walk-forward |
| OPTIONS / GREEKS / GAMMA / GEX / DEX / IV / PAYOFF | Typed demo/file chains and financial regressions | Full units/expiry/coverage/limits/provider contracts |
| DATA DROP / CATALOGUE / AGENT / BROKER | Approved hash-pinned imports and outbound paper read-only bridge | Complete Windows lifecycle, reader and real-data onboarding acceptance |
| REPORT XLSX / PPTX / PDF | Authenticated owned jobs, pinned sources and private files | Complete model/deck content and rendered-artifact review |
| AUTH / HEALTH / BACKUP / SETTINGS | Private access, observed service health, isolated restore | Remaining races, dashboard inventory, final production smoke |

Provider-dependent states must remain truthful. Local demo/file readiness is not
evidence of a live connection. No trading workflow may transmit broker actions.
