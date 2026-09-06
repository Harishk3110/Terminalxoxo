# Terminal Status

Controlling scope: PRD_TERMINAL_ONLY.md, 2026-09-07. The previous second-frontend
scope is cancelled. The 25K line-count target is not a completion certification.

## Verified Terminal-only Checkpoint

Recovery tag pre-terminal-only-cleanup is pushed. All visitor-app source is removed.
One workspace frontend remains. Private root redirects to /overview; unauthenticated
requests redirect to /login. The API requires sessions even for local demo and
legacy /api investment aliases. Noindex and no-store are enabled.

Next.js 15.5.24 production build on Node 22: passed. Workspace lint passed.
31 existing API integration tests passed after authenticating their test clients.
27 access tests passed, including legacy-alias rejection.
Two browser checks passed: unauthenticated root/privacy and retired routes/noindex.

Port 3000 was stopped. The old ignored app build/cache directory could not be
removed because recursive deletion was policy-blocked. Source is absent from the
active Git tree; physical directory absence is NOT claimed.
The private 3001 launcher remains policy-blocked from the previous session.
API 8000 was restarted: health returned 200; anonymous current and legacy
portfolio endpoints returned 401. The real database remains in place.

## Continuing Work

The guarded SGD 100,000 demo correction is applied and its SQLite backup verified.
Original 16 transactions, 9 transaction details, 23 valuation runs and 1 analysis
run are unchanged. NAV at the coherent demo close is SGD 100,597.57, BALANCED.
Exact Decimal valuation curves now feed the interactive performance workspace.
83 focused accounting/performance tests and 231 frontend tests passed. Six
performance-domain files passed strict mypy. The broader sprint run passed 595
and exposed one stale anonymous-actor assertion; all 30 context tests passed after
fixing that assertion. The API suite passed 93 and exposed one direct-call test
requiring authentication; all five broker-agent tests passed after correction.
Three operating browser checks passed, followed by three performance/privacy
checks after visual fixes. Desktop/mobile screenshots were inspected; percentage
formatting and mobile toolbar overlap were corrected. Node 22 build passed.

NAV, lots, corrections, cash, imports, research and saved analysis
engines are retained. Their complete new acceptance workflow is not yet certified.
Whole-backend lint/type failures from the earlier baseline remain disclosed.
Docker Linux daemon was unavailable; Vercel CLI was logged out; no cloud URL is
verified. Existing local data and historical runs are retained.
