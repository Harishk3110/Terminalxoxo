"""Retired standalone demo exporter. Reports are served by the private API."""

from fastapi import FastAPI, HTTPException

app = FastAPI(title="KnK Report Engine", version="0.3.0", docs_url=None, redoc_url=None)


@app.get("/health/live")
def live():
    return {"status": "live", "service": "report-engine", "rendering": "DISABLED"}


@app.get("/health/ready")
def ready():
    raise HTTPException(
        503, "Standalone renderer disabled; private API handles existing XLSX reports"
    )


@app.post("/reports")
@app.get("/reports/{report_id}/download")
def disabled(report_id: str | None = None):
    raise HTTPException(
        403, "Use authenticated terminal report routes; standalone demo exports are disabled"
    )
