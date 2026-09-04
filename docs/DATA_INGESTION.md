# Data Ingestion

## Implemented Flow

Demo and FRED ingestion both preserve raw payloads before normalization.

Demo:

`deterministic fixture -> raw/demo/seed.json -> RawObject -> instruments/prices/fx/macro/portfolio/jobs/datasets -> APIs -> terminal UI`

FRED:

`httpx request -> raw/fred/{series}/{type}/{uuid}.json -> RawObject -> MacroSeries/MacroObservation/MacroVintage -> provider/job state -> macro dashboard`

Uploads:

`UploadFile -> object storage -> RawObject -> UploadedFile -> Dataset -> DatasetVersion -> DatasetColumn -> preview response`

## Supported Uploads

The API process currently parses:

- CSV
- JSON

XLSX and Parquet are routed as future worker-side parsing tasks and are tracked as incomplete in `TASKS.md`.

## Quality And Provenance

Persisted records include provider/source fields, quality labels, timestamps, and raw object references where available. Demo records are labelled `DEMO DATA`; FRED-ingested records are labelled `EOD DATA`.

## Job State

`ingestion_jobs` supports `PENDING`, `QUEUED`, `RUNNING`, `RETRYING`, `SUCCEEDED`, `FAILED`, and `CANCELLED`. The data worker consumes Redis list `knk:jobs` and updates persisted job progress/status.
