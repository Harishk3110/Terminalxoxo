from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="KnK Report Engine", version="0.1.0")


class ReportRequest(BaseModel):
    report_type: str
    source_dataset: str = "local-demo-fixtures"


@app.get("/health/live")
def live():
    return {"status": "live", "service": "report-engine"}


@app.get("/metrics")
def metrics():
    return "knk_report_requests_total 0\n"


@app.post("/reports")
def create_report(payload: ReportRequest):
    return {
        "status": "queued",
        "report_type": payload.report_type,
        "source_dataset": payload.source_dataset,
        "quality": "DEMO DATA",
        "outputs": ["xlsx", "pptx", "pdf"],
    }
