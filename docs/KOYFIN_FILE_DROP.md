# Koyfin File Drop

Koyfin integration is through manually exported CSV/XLSX/JSON files.
There is no direct Koyfin API, scraping, stored Koyfin password or live feed.

Open DATA / Data Drop, upload or drop files, select a mapping profile and inspect
raw preview. Empty mapping applies documented header aliases. Review explicit
defaults and filename/content conflicts, then validate. Supply a dataset name,
permitted-use/licence note and explicit approval before importing. Previously
approved versions are immutable.

Filename hints accept SYMBOL_DATE_type with underscore/space/hyphen separators,
including YYYY-MM-DD and YYYYMMDD. Symbols are checked against the security
master and file content; conflicting symbols require CONTENT or FILENAME
resolution. Filename dates are hints, not a substitute for record dates.

Price imports affect source-selected quotes, histories and NAV. Fundamental
imports retain period, frequency, units, scale, actual/estimate and report date;
missing imported metrics do not fall back to demo statements. DCF requires
complete annual actual FCF/debt/cash/shares. Other curated profile types remain
reference/research datasets where no downstream analytical consumer exists.
Only use exports permitted by the originating service's licence.
