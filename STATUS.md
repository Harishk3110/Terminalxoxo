# STATUS

Date: 2026-09-06
Product: KnK Capital Terminal / KnK Capital
Repository: https://github.com/Harishk3110/Terminalxoxo
Branch: main. Baseline before UI work: 71bd4df.

## Delivery
The terminal shell and core demo/research workflows are rebuilt. This is not full completion of every specialist function in the supplied PRD.

- Full-height black/amber command, security, tabs, rail, analysis, inspector and status layout.
- 24 page/view components; 102 canonical functions across 92 registry route patterns.
- 17 available operational functions, 31 demo analytical, 42 provider-required, 12 in development.
- Persisted workspaces and per-tab state; shared tables/charts, fuzzy commands and security context menus.
- Dynamic ledger-based performance/risk; immutable stress runs; isolated configurable backtesting.py jobs.
- Validated CSV/JSON/XLSX imports and dataset versions; source-labelled synthetic financials, DCF, comparables, private notes, workbook/Pine exports.
- Migration 0002 adds workspace states, analysis runs and fundamental snapshots.
- Public site styling and read-only broker boundary preserved. Public app only gains configurable build output and exclusion of generated logs from type scanning.

## Verification
| Gate | Latest result |
| --- | --- |
| Backend tests | 31 passed; 3 framework deprecation warnings |
| Vitest | 8 passed across domain, registry and workspace tests |
| No-execution scan | Passed |
| Monorepo typecheck | Passed |
| Monorepo lint | Passed without warnings |
| Public production build | Passed using KNK_PUBLIC_DIST_DIR=logs/public-v2-build |
| Terminal production build | Passed using KNK_NEXT_DIST_DIR=logs/terminal-v2-verified; first-load bundle 172 kB |
| Browser journeys / visual regression | 10 passed in 4.2 minutes; 33 existing image baselines compared; 0 skipped, unexpected or flaky tests |
| Alembic | Default database upgraded; clean test upgrade / downgrade-to-0001 / upgrade passed |
| Compose configuration | Passed |
| Full Docker startup | Not run: Docker Desktop Linux engine unavailable |
| Live providers | Not run: credentials/connections absent |

Earlier browser passes identified a first-load fundamentals race, a portfolio refresh race after a rapid manual transaction, and mobile panel/KPI layout issues. All were fixed. The final run used a fresh isolated database and no snapshot-update flag; evidence is recorded in docs/VISUAL_ACCEPTANCE.md. Older CORE_ACCEPTANCE.md and BUILD_EVIDENCE.md describe the V1 run, not this delivery.

## Limits
- Demo price histories and transaction fixtures are independent; inherited performance can be unrealistic and is not investment performance.
- No live brokerage execution, options repricing, portfolio optimizer, AI provider, news feed or verified live market data.
- No arbitrary user-code execution, walk-forward optimization, factor IC, attribution engine, WACC builder or full structured thesis model.
- No PDF/deck builder, Parquet/Arrow/ZIP ingestion or complex docking/link groups.
- Table views are browser-local; workspaces have no conflict merge or per-user isolation.
- Production security hardening, TOTP lifecycle and distributed worker supervision remain outstanding.
- Most specialist function limitations are visible in the function registry, not hidden behind generic Overview routes.

## Local Runtime
The local API was restarted with the final code on http://127.0.0.1:8000 and verified live: 102 functions, 20 demo quotes and nine workspaces. Background terminal launch was blocked by the session execution policy; a web server on 3001 must be started by the user using the README command. Browser tests used isolated temporary services on 8001/3002 and separate databases, not the working ledger. Both test ports were confirmed closed after the final run.

## Evidence
Design/behavior: docs/PRD_TERMINAL_UI.md and the companion shell, registry, workspace, data and stress docs.
Visuals: docs/screenshots; regression baselines: tests/e2e/terminal.spec.ts-snapshots.
Machine-local test report: logs/terminal-e2e-results.json (ignored by Git).
