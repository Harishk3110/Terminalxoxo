# Price Freshness

Each selected observation records source/category, source file, dataset version,
observation time, ingestion time, original state, current state, adjustment
state and age in hours. Default stale threshold is 72 hours, configurable per
instrument. This is an explicit tolerance, not a market-calendar freshness SLA.

FILE IMPORT means an approved exported file, never a live feed. KOYFIN FILE is
the source label for Koyfin mapping profiles. Demo observations remain DEMO DATA.
A stale selected observation is retained and shown as STALE; the portfolio is
CALCULATED WITH STALE DATA. Stale market value and NAV percentage are reported.
Missing prices/FX invalidate full NAV; no zero-price or cross-currency 1.0
substitution is used. Risk using stale carried observations may understate
variation and carries a warning.

NAV calculated_at is distinct from data as_of. Health reports the most recent
persisted calculation, not a hardcoded fresh NAV or live market status.
