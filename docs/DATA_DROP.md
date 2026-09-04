# Data Drop

The terminal Data Drop page calls `POST /api/v1/uploads`.

## Implemented

- CSV upload.
- JSON upload.
- File size guard at 25 MB.
- Immutable original object stored through `ObjectStorage`.
- SHA-256 content hash.
- Raw object row.
- Uploaded file row.
- Dataset and dataset version rows.
- Column inference for date/number/string fields.
- Preview rows returned to the browser.
- Dataset catalogue reads persisted dataset rows.

## Not Yet Implemented

- XLSX parsing in the API process.
- Parquet parsing.
- PDF/image research attachment workflow.
- Interactive column mapping confirmation before import.
- Worker-side quarantine review UI.

Unsupported tabular formats return a clear error and are tracked for worker-side parsing.
