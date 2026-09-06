# Koyfin File Import

Koyfin support is a lawful file/attachment workflow, not a scraped or fabricated
live API. Data Drop accepts CSV, XLSX, XLS, Parquet, JSON and JSONL. The outbound
Windows agent watches a configurable root, waits for stable files, hashes bytes,
queues retries durably, uploads with scoped credentials and archives only after
server acknowledgement. No real-data path or credential belongs in Git.

Use KOYFIN_PRICE_HISTORY, KOYFIN_EQUITY_SNAPSHOT, KOYFIN_WATCHLIST_EXPORT,
KOYFIN_TECHNICAL_EXPORT, KOYFIN_FUND_EXPORT or KOYFIN_MACRO_EXPORT as appropriate.
The user reviews the mapping, filename/content symbol conflicts, validation and
licence note before approving each version. Raw bytes never change. Competing
values remain stored. Price observations carry FILE IMPORT and KOYFIN FILE,
filename, observation time, ingestion time and dataset version. A stale file is
not silently replaced with demo data. Position files are references, not holdings.

Fundamental imports require explicit unit, scale, period, frequency, actual/
estimate flag and report date. Partial restatements retain metric-level lineage.
Options require the contract schema in OPTIONS_DATA.md. Imported corporate
financials and estimates are research sources, not audited company accounts.
Current daily-file timestamps use 20:00 UTC as a disclosed convention. Intraday
file OHLCV is not separately modeled; use the read-only provider timestamp contract
for observed timestamps. Custom feature tables remain available through Catalogue
uploads; Data Drop's named profiles are not a universal arbitrary-schema mapper.

Research theses accept PDF/PNG/JPG/WebP attachments with byte limits, image-format
checks, immutable hashes and authenticated attachment-only downloads. PDFs have
signature/trailer validation, not malware scanning. All are UNSCANNED_ATTACHMENT;
do not treat parser validation as a security certification. Uploaded files can be
linked to immutable thesis revisions. There is no public publishing endpoint.

## Local Agent

KNK_DATA_DROP_ROOT has no hardcoded username or OneDrive path. The agent creates
inbox/{koyfin,prices,fundamentals,positions,transactions,options,macro,custom}, plus
processing, review, processed, rejected, quarantine and logs. It retains the older
portfolio inbox for compatibility. SCAN_INTERVAL_SECONDS defaults to five and is
bounded to 1-3600 seconds. AUTO_UPLOAD and ARCHIVE_PROCESSED respect false. Automatic
import is deliberately rejected when requested; explicit server approval remains
mandatory. Pairing is single-use, expires and can be revoked. Tokens stay in the
OS credential vault; they have no general investment or execution authority.

Run the existing services/local-agent/agent.py CLI with --root and --url. Use
--allow-loopback-http only for local development. A PAUSE marker halts scanning,
uploading and archive synchronization while retaining heartbeats. Import approval,
parser failures, retries and archive states remain observable in Data Drop.
