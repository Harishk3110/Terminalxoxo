# Data Source Precedence

Prices: BROKER, PROVIDER, FILE, DEMO. Per-instrument rules and a preferred source
can override this order, with a required reason and audit entry. Same-date
alternative prices remain available; differences above 1% are flagged.

An existing selected FILE observation is carried forward even when a newer
demo observation exists. An explicitly preferred missing source does not fall
back to demo. Unknown values remain unavailable. Quotes, NAV, histories and
factor inputs use the same source resolver.

AUTO account view uses a fresh, scoped IBKR Paper account snapshot before the
INTERNAL LEDGER. Freshness requires both snapshot and nonrevoked agent heartbeat
within 90 seconds. Offline snapshots do not masquerade as connected balances.
Broker-history performance, attribution and risk are unavailable; they are never
borrowed from the demo book. Explicit ?view=INTERNAL retains ledger analytics.
Reported prices have account-snapshot timestamps, not verified exchange times.
Imported positions are reference datasets, not position overrides. Real TWS
connectivity remains unverified without the user's configured paper account.

Demo reset creates a DEMO_ONLY profile so retained external files do not alter
the reset fixture. A later explicitly approved price/FX import returns that
profile to AUTO, with an audit record. Global price preferences still apply to
security quote views.

Price Sources & Portfolio Controls is available from Data Drop. API:
GET/POST /api/v1/operations/sources/{symbol}. History is restated from accepted
source versions; use pinned dataset versions for reproducible research.

Validated JSON-provider price imports append PROVIDER observations with exact
timestamps, state and version. They do not overwrite FILE/DEMO records or mutate
transactions. Connection success is distinct from market-data freshness.
SEC submissions/XBRL facts are a separate immutable archive, not yet curated FIN
inputs. The requested SEC-first fundamental selection is therefore not claimed;
approved file financials retain their current metric-level precedence. FX uses
existing resolver priority and stale provenance; independent per-pair priority
configuration is not implemented. These remain explicit acceptance gaps.
