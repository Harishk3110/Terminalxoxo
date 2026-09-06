# Terminal V2 Visual Acceptance

Date: 2026-09-06. Final regression: 10 tests passed in 251.7 seconds, with zero failures, skips or flaky tests. All 33 existing screenshot baselines passed comparison without a snapshot-update flag.

## Coverage
- Overview, Macro, Portfolio, Performance, Risk, Stress, Hedge and Backtests.
- 1366x768, 1440x900, 1920x1080 and 2560x1440.
- Mobile monitoring at 390x844, with inspector initially closed.
- Outer scroll containment, fixed 40px header, rendered chart dimensions and nonblank desktop canvas pixels; visible mobile heading/chart and nonzero main-panel dimensions.
- Security-aware commands and keyboard controls; workspace duplication/restoration; stress inputs/results/audit/export; manual transaction refresh; file validation/import/backtest; table views/context menu/panel resize; workbook generation; login/logout; provider/health navigation.

## Artifacts
Unmasked review images are under docs/screenshots. Thirty-three Windows/Chromium regression baselines are under tests/e2e/terminal.spec.ts-snapshots. Time/latency/UUID-dependent regions are masked for comparison. Chart geometry and all substantive analysis remain visible. Test failures retain traces/screenshots in the OS temp directory's knk-terminal-e2e folder (overridable with PLAYWRIGHT_OUTPUT_DIR); JSON results are saved in logs/terminal-e2e-results.json.

The palette, forms, column tools and inspector were exercised by Playwright, not inferred from a successful build. In-app browser integration was unavailable in this session; the repository's Playwright runner was used instead.

## Reproduction
From the repository root in PowerShell:

```powershell
$env:KNK_NEXT_DIST_DIR='logs/terminal-v2-verified'
corepack pnpm --filter @knk/terminal-web build
$env:PLAYWRIGHT_DIST_DIR='logs/terminal-v2-verified'
corepack pnpm test-e2e
```

The runner starts isolated API/web servers, refuses occupied test ports, creates its own SQLite database/object store, and explicitly terminates its child processes. Keep dev/test/build output directories separate. To reapprove intentional image changes, append --update-snapshots; do not use that flag for a normal regression run.

## Disposition
The final normal run started at 2026-09-06 04:49:21 UTC against a fresh isolated database and the terminal-v2-verified production build. All ten tests and 33 image comparisons passed. Temporary API/web servers were confirmed stopped afterward. Desktop Overview, Stress and Backtest images and the final mobile image were also manually inspected.

Initial passes exposed and corrected a concurrent fundamentals insert, stale portfolio results after a fast transaction, and an inspector covering mobile content. Manual image review caught a mobile CSS selector collapsing the main panel when the inspector was absent, then overlapping narrow KPI cells. The selector is scoped to the inspector and mobile KPIs use a two-column grid, with visible-content and text-containment assertions. Earlier test-only stale-run polling was corrected to wait for the new run ID before evaluating results. Playwright worker cleanup stalled inside OneDrive; transient artifacts now use OS temp storage. No claim is made for Firefox engine coverage, full production security, provider credentials or container startup.
