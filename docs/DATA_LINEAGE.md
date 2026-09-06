# Data Lineage

ExternalFile is the durable inbox record. FileHash enforces byte-level global
deduplication; duplicates point to the original record. UploadedFile stores the
immutable original bytes and SHA-256, including original XLSX content.

States: DETECTED, HASHING, UPLOADING, STORED_RAW, PREVIEWING, SCHEMA_DETECTED,
MAPPING_REQUIRED, MAPPED, VALIDATING, VALIDATED or VALIDATED_WITH_WARNINGS,
AWAITING_APPROVAL, IMPORTING, IMPORTED, ARCHIVED. Error/terminal branches:
DUPLICATE, REJECTED, QUARANTINED, UPLOAD_FAILED, VALIDATION_FAILED, IMPORT_FAILED.

Every transition records time and explanation. Import revalidates, writes an
immutable normalized JSON object, creates DatasetVersion/Columns/Lineage and
posts eligible price/FX/ledger records atomically. Failed ledger imports retain
the raw inbox record and roll back curated DB changes; orphaned object-store
bytes may require later administrative garbage collection.

Same dataset name, type and source creates the next version. Versions retain
raw hash, curated hash, mapping/profile version, source file, licence and
point-in-time state. Catalogue preview verifies curated bytes and exposes
versions and linked backtests. Backtest input includes the exact version ID;
new imports do not rewrite older results. Imported raw/curated hash checks
detect tampering, not correctness of the external data itself.
