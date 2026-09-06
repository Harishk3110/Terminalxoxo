# Provider Connections

Settings > Connections is private. Five adapters have persisted enable/disable,
local revocation, observed tests and read-only imports. Credentials are environment
or deployment-secret settings, never API responses. Enabling is not a successful
test. A successful test is not evidence that all portfolio data are live. Last sync
age is distinct from market-observation freshness. Runtime failures and rate limits
have sanitized health/request records and audit entries.

| Adapter | Server configuration | Read operations |
| --- | --- | --- |
| FRED | FRED_API_KEY, FRED_ENABLED | Metadata, observations, vintages, backfill |
| SEC EDGAR | SEC_USER_AGENT="Organization contact@example.com", SEC_ENABLED | Recent submissions and company XBRL facts |
| OpenFIGI | OPENFIGI_ENABLED; optional OPENFIGI_API_KEY | Identifier mapping and explicitly reviewed assignment |
| Market JSON | MARKET_DATA_BASE_URL, optional MARKET_DATA_API_KEY, MARKET_DATA_ENABLED | /prices |
| Options JSON | OPTIONS_DATA_BASE_URL, optional OPTIONS_DATA_API_KEY, OPTIONS_DATA_ENABLED | /options/chain |

Persisted controls override initial environment enable flags. Revoke only blocks
this application; rotate/revoke keys at the vendor separately. Disabled FRED also
blocks the older macro routes and worker ingestion. Existing imported data remain.
The HTTP transport has finite timeouts, bounded retries and 25 MB decompressed
response limits. It does not follow redirects or expose upstream bodies in errors.
429 is recorded without repeated immediate requests. Pacing is per API process;
multi-replica deployments need a shared rate limiter before increasing concurrency.

SEC uses fixed data.sec.gov read-only endpoints and a real operator-supplied contact
identity. Recent submissions are not a complete historical crawl. Older archive
filenames are returned for coverage review; recursive historical ingestion is not
implemented. Raw XBRL facts retain taxonomy, unit, reporting dates and accession;
they are NOT automatically mapped into the curated FIN/DCF statements. SEC does
not require an API key. https://www.sec.gov/search-filings/edgar-application-programming-interfaces

OpenFIGI allows anonymous mapping with lower limits. Requests are limited to ten
jobs without a key or 100 with one. Multiple candidates remain REVIEW_REQUIRED;
only an administrator's explicit selection assigns a FIGI. Existing conflicting
identifiers are rejected. Request/result hashes and approval evidence persist.
https://www.openfigi.com/api/documentation

## Vendor-Neutral JSON Contract

The market/options adapters are concrete HTTP adapters for a server-owned gateway
implementing this schema. They are not drop-in adapters for every vendor. URLs must
be HTTPS without embedded credentials/query strings. Optional bearer keys stay
server-side. A request sends symbol and optional start/end date parameters. The
response is an object containing rows, not arbitrary vendor-specific JSON.

Market rows require symbol, timezone-aware timestamp, positive close, currency,
data_state (EOD/DELAYED/LIVE), adjustment_state (UNADJUSTED/ADJUSTED); optional
open/high/low/volume are validated. Wrong symbols/currencies, duplicates, future
timestamps, nonfinite values and invalid OHLC are rejected. Imports append source-
versioned PROVIDER observations, preserving competing FILE and DEMO values.
Options rows follow OPTIONS_DATA.md, bounded to 2,000 observations per response.
The user must obtain appropriate vendor licences; no vendor entitlements are implied.

The default managed demo remains DEMO_ONLY until the user approves external
sources; security source selection is separate from portfolio price mode. Review
Price Sources & Portfolio Controls when switching a book to connected data.
IBKR and Local Data Agent pairing remains in the dedicated read-only agent views.
Infrastructure/provider services without probes are not falsely marked connected.
Dedicated news, AI, fundamental and FX vendor adapters are not connected here.
