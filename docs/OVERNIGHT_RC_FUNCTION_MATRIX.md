# Overnight Function Matrix

This is an implementation/evidence map, not release certification. Read the status,
task checklist and build evidence together. No live-provider or cloud-deployment
verification is implied. Every trading workflow remains manual/read-only.

| Workspace | Route | Implemented source/workflow | Evidence and remaining gate |
| --- | --- | --- | --- |
| Overview | /overview | Ledger-backed capital, balances, positions, observed status | performance/operating browser tests; complete M4 certification open |
| Portfolio | /portfolio | Manual transactions, corrections, lots, accounting inspectors | ledger, directory, exposure, NAV and position browser tests; full release rerun required |
| Performance | /performance | Saved valuation returns, benchmark and decomposition | performance browser/backend tests; broader attribution acceptance open |
| Alpha | /alpha | Saved return-source regression with sample/window diagnostics | quant-research tests; populated visual matrix in progress; PIT scope open |
| Equity | /equity | Holdings, coverage, saved valuations and research links | equity-research tests; segments/ROIC/forward estimates remain partial |
| Quant Dashboard | /quant-dashboard | Saved research and run summaries | operating and quant-research tests; full model/walk-forward scope open |
| Options/GEX | /options/AAPL, /functions/gex | Explicit synthetic fixture or validated chain, Greeks/GEX/payoff | options-research tests; historical/portfolio acceptance incomplete |
| Risk & Trade | /risk-trade-monitor | Internal ledger review, limits and model settings | risk-hedge tests; no transmission capability |
| Stress | /stress-tests | Dated or saved valuation, scenario runs, contribution and export | dated regression and browser passes; full release gate open |
| Hedge | /hedge | Dated sizing and auditable manual review | dated regression and browser passes; not execution or full hedge optimization |
| Data Drop | /data-drop | Validate, license, approve and import files | upload/operating/browser tests and seven template profiles; complete onboarding open |
| Data Catalogue | /data-catalogue | Persisted immutable versions and lineage | dataset integrity tests; all downstream consumer acceptance open |
| Backtest Result | /backtests | Saved next-open offline runs with pinned data/FX/costs | quant-research and lifecycle browser tests; corporate actions/PIT scope open |
| Excel Studio | /excel-studio | Owned queued XLSX/PDF and pinned source download | report pipeline tests and browser smoke; full model content/render QA incomplete |
| Deck Builder | /deck-builder | Owned queued editable PPTX and source download | report pipeline tests and browser smoke; full IC-deck depth/render QA incomplete |
| System Health | /system-health | Observed API/worker/report/provider/backup states | PostgreSQL private isolated restore and receipt metrics verified; ten dashboards remain open |

Visual coverage now enumerates these workspaces, plus macro and risk, at 1366x768,
1440x900, 1920x1080, 2560x1440 and 390x844. Screenshot generation, nonblank chart
checks and viewport bounds pass in the first expanded run; populated alpha/GEX/
hedge verification and final screenshot review are still being completed. Honest
unavailable/stale states are not reclassified as live or healthy.

Supported broker bridge: `services/local-agent/broker_reader.py`, outbound paper
read-only. `services/broker-agent/agent/main.py` is a retired inbound demo surface
and now refuses pairing/snapshots rather than returning fabricated values.
