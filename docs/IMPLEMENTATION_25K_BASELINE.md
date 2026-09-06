# 25K Sprint Baseline

Recorded 2026-09-06 before sprint implementation.

- Commit: `c3d9e847604fbbfb59df170c1b5f83f7dbec94a1`.
- Branch: `main`; worktree clean at capture.
- Remote: `https://github.com/Harishk3110/Terminalxoxo.git`.
- Machine-readable source, route, endpoint and test-file inventory:
  [baseline-inventory.json](25k/baseline-inventory.json).
- Capture: `python scripts/count_25k_delta.py --inventory --output docs/25k/baseline-inventory.json`.

| Category | Files | Physical lines | Eligible nonblank/noncomment lines |
| --- | ---: | ---: | ---: |
| Backend/domain | 33 | 7,513 | 6,296 |
| Frontend | 30 | 10,889 | 8,760 |
| Workers/agents/reporting/infrastructure | 23 | 918 | 744 |
| Tests | 18 | 1,741 | 1,457 |

These are baseline inventory counts, not new sprint credit. The final counter
also subtracts matching baseline lines across file moves and copies. It cannot
certify semantic quality: substantive integration and test review remain required.

The registry contains 110 functions and 96 distinct route patterns, including
explicit provider-required/in-development entries. Registry presence does not
mean 96 operational product views. Endpoint declarations in the JSON retain
router-local paths; runtime OpenAPI is the authority for mounted API paths.

Baseline release evidence records 66 backend tests, 8 Vitest tests, 12 Playwright
tests and 33 screenshot comparisons. These earlier results are not rerun sprint
acceptance and are not new tests. API statement coverage was 79%.

Compose defines PostgreSQL, Redis, MinIO/init, API, public/terminal frontends,
data/quant workers, report engine, broker agent, workflow engine, Prometheus and
Grafana. The previous release verified only isolated API/PostgreSQL/Redis and
local-object-storage readiness, not the complete stack.

Five pre-existing frontend files exceed 1,200 lines; their exact lengths are in
the inventory. They were inherited, not approved as a pattern for new modules.
Splitting them during the product milestone will not earn moved-code credit.

## Preserved State

The working SQLite ledger contains 16 transactions across the legacy book and
KNK_MAIN. Main opens with an explicit SGD 70,000 contribution. Last verified
demo NAV was SGD 70,597.57, with cash 23,476.64 and securities 47,120.93.
Opening-capital reconciliation difference was 0.00. Market inputs end
2026-09-04 20:00 UTC. No real-time or actual brokerage performance is implied.

No baseline transaction, dataset, valuation or source object may be removed by
this sprint. Corrections must be versioned/audited, not destructive overwrites.
