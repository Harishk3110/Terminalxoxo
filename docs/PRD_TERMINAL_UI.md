# KnK Capital Terminal UI PRD

Date: 2026-09-06. Source: supplied terminal rebuild brief and terminal wireframe.
Brand: KnK Capital. Product: KnK Capital Terminal.

## Target
A full-height investment workstation, not an outer-scrolling dashboard. Desktop shell: 40px command header, 28px security context, 30px tabs, compact function rail, analytical workspace, resizable inspector and 23px system status bar. Core workspaces must fit 1366x768 through 2560x1440. Mobile is a monitoring layout with internal scrolling.

## Required behavior
- Persistent workspaces, reordered/closed tabs, active security context, keyboard command search.
- Canonical function registry used by API, palette and navigation; unsupported functions must be explicit.
- Dense sortable/filterable/resizable virtualized tables and source-labelled charts.
- Working portfolio ledger, performance, risk, stress, hedge, macro, research, data import, backtest and export workflows.
- Persist inputs, calculation version, data timestamp, warnings, results and job history.
- Never show synthetic data as live, broker balances as ledger balances, or execution readiness without a connection.
- Preserve the private terminal and read-only broker boundary; there is no visitor frontend.
- Verify interactions, geometry, screenshots, unit tests, API tests, build and Compose configuration.

## Acceptance boundary
This delivery implements the shell and core demo/research workflows. It is not full completion of every specialist function in the supplied brief. The registry distinguishes 17 available operational functions, 31 demo analytical functions, 42 provider-required functions and 12 in-development functions. See FUNCTION_REGISTRY.md and STATUS.md for explicit limits.
