# Mapping Profiles

Twelve initial version-1 profiles:
KOYFIN_PRICE_HISTORY; KOYFIN_EQUITY_SNAPSHOT; KOYFIN_WATCHLIST_EXPORT;
KOYFIN_TECHNICAL_EXPORT; KOYFIN_FUND_EXPORT; KOYFIN_MACRO_EXPORT;
GENERIC_OHLCV; GENERIC_FUNDAMENTALS_LONG; GENERIC_FUNDAMENTALS_WIDE;
GENERIC_PORTFOLIO_TRANSACTIONS; GENERIC_POSITIONS; GENERIC_FX_HISTORY.

Rules contain aliases, required roles, defaults and approval policy. File
records retain the exact profile ID/version, mapping, explicit defaults and
conflict resolution. Profiles start unapproved and auto_import=false.
Every file version currently requires explicit approval; profile editing and
automatic approved-profile imports are not exposed.

CSV delimiters: comma, semicolon, tab or pipe. XLSX reads the active sheet;
JSON accepts row objects or a rows array. Limits: 25 MB raw, 100 MB expanded
workbook and 100,000 rows. Original XLSX bytes are not converted in raw storage.

Validation checks required fields, known symbols/currencies, positive prices,
OHLC ordering, nonnegative volume, valid nonfuture dates, duplicate records and
gaps. Close-only prices can value NAV but do not qualify for OHLC backtests.
Missing values remain missing. Fundamental scale/unit/frequency/actual-estimate
and report date must be supplied explicitly. Position imports are references,
not editable portfolio holdings.
