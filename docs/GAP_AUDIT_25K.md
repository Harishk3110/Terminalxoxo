# 25K Sprint Gap Audit

Baseline: c3d9e847604fbbfb59df170c1b5f83f7dbec94a1. Approved shell retained.

| Milestone | Existing behavior | Required expansion |
| --- | --- | --- |
| M1 Ledger/NAV | Decimal average-cost ledger, 17 kinds, native economic cash, immutable valuations | FIFO/lots, fee policy, settlement/available cash, reverse splits/mergers, auditable corrections and resource APIs |
| M2 Performance | TWR/MWR, period returns, gated risk ratios | Configurable periods/benchmark/fees, drawdown/recovery episodes, captures/rolling metrics, persisted attribution |
| M3 Sources | Broker/provider/file/demo priority, inverse FX, staleness | Cross FX, configurable freshness policies, persistent field conflicts and overrides |
| M4 Files | CSV/XLSX/JSON, 12 profiles, explicit approval and raw hashes | XLS/Parquet/JSONL/attachments, 13th profile, version editor, quarantine, expanded validation, curated Parquet and consumers |
| M5 Agent | Outbound polling, vault, retry/archive, read-only paper reader | Separate module permissions, resumable uploads, diagnostics, startup/service scripts |
| M6 Providers | FRED observations/metadata and demo registry | Incremental revisions/releases/vintages, SEC, OpenFIGI, rate state and optional provider adapters |
| M7 Trades | Review, pre/post snapshots, mock broker reconciliation | Typed comparison engine, all break classes, assignment/statement matching and audit lifecycle |
| M8 Risk | Current-weight covariance/historical VaR | EWMA, rolling statistics, parametric/Monte Carlo tails, full exposures and persisted limit breaches |
| M9 Stress/hedge | Linear beta/FX/TLT scenario jobs, frontend ETF estimate | Domain hedge/futures/sector/currency/rebalance, fees/residuals and expanded scenario decomposition |
| M10 Backtest | Persisted single-security MA template | Multi-security/currency accounting, portfolio construction, ten strategies, cancellation/progress and rich outputs |
| M11 Research labs | Momentum IC/quintiles, research candidate records | Full factor diagnostics, model training/artifacts, evidence-based review states |
| M12 Robustness | Purged fixed IS/OOS factor split | Rolling/expanding walk-forward and bootstrap Monte Carlo services |
| M13 Equity | Synthetic/curated statements and simple DCF | Period/TTM alignment, full forecasts/WACC/comps, identifiers and structured theses |
| M14 Pine | One MA script | Four templates, compatibility/version history, signal parity and non-executing webhook review |
| M15 Reports | Basic synchronous workbooks | Isolated requests, formula-driven models, risk/quant sheets, PPTX/PDF/chart packages |
| M16 Product | Seven dense operating desks | Fully integrated workflows, portfolio selectors/corrections, richer catalogue/research/health panels |
| M17 Search | Securities/functions, keyboard tabs/workspaces | Cross-entity search, relevance boosts, favourites/recent commands and intent routing |
| M18 Database | Three migrations and broad baseline tables | Constrained, indexed, versioned models actually consumed by each milestone |
| M19 Jobs | Persisted subprocess analytics | Redis-backed durable claims/retries/cancellation, all job types, SSE and worker supervision |
| M20 Operations | Basic probes and Prometheus counters | Full metrics/Grafana, measured latency, backups/restores and complete Docker validation |

Existing broker/reference separation, source honesty and no-execution boundary
are regression requirements. Missing live credentials must not block mock/contract
implementation. Live smoke tests will be reported separately from local checks.

No new financial engine will be placed in React or HTTP handlers. New domain
modules will remain bounded and typed, with assertions against independently
calculated examples and invariants rather than implementation-shaped echoes.
