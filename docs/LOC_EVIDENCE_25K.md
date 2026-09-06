# LOC Evidence 25K

Baseline c3d9e847604fbbfb59df170c1b5f83f7dbec94a1; main; 2026-09-06.

Command: `python scripts/count_25k_delta.py --check --output logs/25k-loc.json`.
Exit 1 is expected until every category and the total reach the stated floors.
No complete milestone is certified. Documentation/JSON inventory is excluded.

Counted lines must be non-generated eligible source/test lines, not blank lines,
comment/docstring-only lines, structural punctuation, or relocated baseline code.
The automated count does not replace the substantive-code review requirement.
The counter credits a normalized new line at most once globally and only if it
does not occur anywhere in baseline source. Copies and file moves receive no
credit. These conservative totals can be lower than ordinary added-line counts.

| Milestone/commit/date | Backend | Frontend | Worker/agent/report/infra | Tests | Total | Gates |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| Baseline c3d9e84 / 2026-09-06 | 0 | 0 | 0 | 0 | 0 | NOT MET |
| M1 interim worktree / 2026-09-06 10:42 UTC | 1274 | 524 | 263 | 1351 | 3412 | NOT MET |
| M1 checkpoint e25b94e / 2026-09-06 11:22 UTC | 1723 | 790 | 263 | 2164 | 4940 | NOT MET |
| M1 storage-boundary follow-up / 2026-09-06 11:38 UTC | 1762 | 790 | 263 | 2239 | 5054 | NOT MET |
| M1 transaction context and entry/detail workflows / 2026-09-06 12:15 UTC | 1908 | 1222 | 263 | 2882 | 6275 | NOT MET |
| M1 position-period P&L / 2026-09-06 12:26 UTC | 2045 | 1222 | 263 | 3089 | 6619 | NOT MET |
| M1 native/base metrics and saved-run inspector / 2026-09-06 12:46 UTC | 2186 | 1472 | 263 | 3502 | 7423 | NOT MET |
| M1 portfolio creation and scoped directory / 2026-09-06 13:05 UTC | 2206 | 1820 | 263 | 3938 | 8227 | NOT MET |
| M1 correction storage and audit follow-up / 2026-09-06 13:11 UTC | 2238 | 1820 | 263 | 4010 | 8331 | NOT MET |
| M1 grouped exposures, broker boundary and historical cache / 2026-09-06 13:45 UTC | 2436 | 2004 | 263 | 4654 | 9357 | NOT MET |

Interim command: `.venv-sprint/Scripts/python.exe scripts/count_25k_delta.py --output docs/25k/current-delta.json`.
Exit 0 means the report was produced; it does not mean the gates passed. The report
explicitly says `line_gates_passed: false` and `semantic_review_required: true`.

Latest command included `--check`; exit 1 correctly reports unmet category and
total floors. Screenshots, migration-test databases, fixtures, baseline code moved
to shared modules, build artifacts and these evidence documents receive no credit.
