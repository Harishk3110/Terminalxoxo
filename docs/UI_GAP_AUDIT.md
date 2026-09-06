# Terminal UI Gap Audit

Audit date: 2026-09-06. Baseline: 71bd4df.

## Observed defects

- One catch-all component owns the shell and nearly every screen. Unknown routes silently render Overview.
- The page uses an outer scrolling, navy card layout. Navigation is 260px wide, headers and panels are oversized, and responsive utility styles can stack the navigation above the content.
- There is no persistent security context, terminal tab strip, workspace persistence, command palette, inspector, or measured system status bar.
- Stress, hedge, catalogue, jobs and security-master views print JSON. Stress has no scenario form or run action.
- Macro range/export labels are inert spans. Backtests have no configuration or job workflow. Upload immediately imports without preview or mapping.
- Function definitions are duplicated between the frontend, backend and registry; advertised functions can resolve to unrelated pages.
- Existing API clients omit cookies and cancellation and flatten structured API failures into status messages.
- Portfolio, performance and risk APIs exist, but risk/performance calculations use fixed demo return lists. Demo stress results are static. Overview incorrectly labels a strategy backtest as its main portfolio curve.
- Health checks mix actual probes with unverified worker/provider status. Missing credentials must remain visibly unavailable.
- Existing browser coverage tests only three page labels and has no geometry or screenshot assertions.

## Rebuild scope

Replace the terminal's styling and shell independently of the public website. Introduce shared dense panels, virtualized tables, chart tokens and a canonical function registry. Add persisted workspaces and analytical runs, security data/provenance endpoints, dynamic stress calculations and configurable dataset-backed backtests. Rebuild core financial, data, research and operations screens and label unsupported/provider-dependent functions honestly. Verify actual interactions, desktop geometry and screenshots; record exact results and remaining limitations separately.
