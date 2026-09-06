# Terminal Architecture

One Next.js frontend, apps/terminal-web, uses shared domain, terminal-function,
search, design-system and API-client packages. Root navigation redirects to the
Portfolio Command Centre. No visitor-facing investment frontend is retained.

The server validates the HTTP-only session before rendering a private route.
FastAPI separately authenticates every /api/v1 investment endpoint, in all modes.
The sign-in/session endpoints do not return investment data. Agent ingestion uses
scoped, revocable bearer credentials under /agent/v1, not browser sessions.

The ledger, price resolver, FX resolver, immutable valuation runs and accounting
subledgers remain authoritative. PostgreSQL is the full-stack database; SQLite
supports local operation and isolated tests. Redis and object storage support
durable workers and imported artifacts. No frontend embeds a current NAV constant.

Data and quant workers execute research jobs. Reports are internal artifacts.
Quant inputs are immutable hash-verified object-store datasets; the worker dispatch
is an explicit allowlist. Offline Backtrader handles simulated fills, statsmodels
handles alpha inference and scikit-learn handles purged model evaluation. These
research engines do not share any execution channel with IBKR.
IBKR synchronisation reads paper-account data and supports manual reconciliation;
there are no broker order-execution methods.

Settings retain per-provider capability and freshness states. A connected provider
does not change unrelated datasets to LIVE. See PRD_TERMINAL_ONLY.md and
TERMINAL_ACCEPTANCE.md for required scope and measured coverage.

Equity research uses immutable AnalysisRun results for Decimal FCFF/WACC,
source-pinned peer comparisons and structured thesis revisions. Matching thesis
references preserve legacy ledger foreign keys; no historical research is removed.
Imported financials preserve metric-level source lineage and frequency semantics.
