# Options Data

Import CSV/XLSX/JSON through Data Drop with GENERIC_OPTIONS_CHAIN. The existing
raw-object hash, mapping preview/validation, explicit approval, immutable curated
version and lineage workflow is reused. Imports never create portfolio holdings.

Required fields: underlying symbol, unique option symbol, expiry, strike, CALL/PUT,
contract multiplier, EUROPEAN/AMERICAN exercise style, timezone-aware quote
timestamp and IV unit (DECIMAL/PERCENT). Currency comes from the security master
unless explicitly supplied. Bid, ask, last, IV, integer volume/OI, signed OI change
and provider Greeks are optional. Missing market fields remain null.

Expiry time defaults to 20:00 UTC if absent. This is a disclosed convention, not
an exchange calendar. Supply expiry_time_utc for accurate maturity. Crossed quotes,
negative OI, nonfinite values, invalid IV units, future timestamps and conflicting
contract specifications are rejected. At an analysis cutoff, only the latest
observation no later than that cutoff is selected per contract.

The private /options workspace provides chain, GEX, Greeks, volatility, payoff
and selected-underlying positions. Calculation is explicit and saved; source,
hash, quality, observation time, calculation time, exclusion counts and assumptions
remain visible. Missing chains return DATA UNAVAILABLE. There is no automatic
demo fallback. Local-demo/test users can explicitly create a synthetic European
chain; it is marked DEMO DATA and cannot run in production. Synthetic quotes and
open interest are never represented as observed exchange data.

Production options-provider credentials and licensing are not connected. OI flow
and historical volatility cones still require historical datasets and are not
marked available. Intraday exchange calendars, American pricing, discrete dividends,
smile interpolation, assignment and complete multi-underlying portfolio options
risk are not implemented. No execution endpoint or broker order control exists.
