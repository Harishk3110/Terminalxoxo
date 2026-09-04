from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from pathlib import Path

import xlsxwriter
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel

app = FastAPI(title="KnK Report Engine", version="0.2.0")
REPORT_ROOT = Path("generated-reports")
REPORT_ROOT.mkdir(exist_ok=True)


class ReportRequest(BaseModel):
    report_type: str
    source_dataset: str = "local-demo-fixtures"


@app.get("/health/live")
def live():
    return {"status": "live", "service": "report-engine"}


@app.get("/metrics")
def metrics():
    return PlainTextResponse("knk_report_requests_total 1\n")


@app.post("/reports")
def create_report(payload: ReportRequest):
    report_id = str(uuid.uuid4())
    path = REPORT_ROOT / f"{report_id}.xlsx"
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {"in_memory": True, "strings_to_formulas": False})
    header = workbook.add_format({"bold": True, "bg_color": "#D9EAF7"})
    money = workbook.add_format({"num_format": "SGD #,##0.00"})
    overview = workbook.add_worksheet("Overview")
    overview.freeze_panes(1, 0)
    overview.write_row(0, 0, ["Field", "Value"], header)
    overview.write_row(1, 0, ["Report Type", payload.report_type])
    overview.write_row(2, 0, ["Source Dataset", payload.source_dataset])
    overview.write_row(3, 0, ["Quality", "DEMO DATA"])
    overview.write_row(4, 0, ["Generated At", datetime.now(timezone.utc).isoformat()])
    holdings = workbook.add_worksheet("Holdings")
    holdings.write_row(0, 0, ["Symbol", "Market Value"], header)
    holdings.write_row(1, 0, ["AAPL", 16972.61])
    holdings.write_number(1, 1, 16972.61, money)
    sources = workbook.add_worksheet("Sources")
    sources.write_row(0, 0, ["Provider", "Dataset", "Quality"], header)
    sources.write_row(1, 0, ["KnK deterministic fixture", payload.source_dataset, "DEMO DATA"])
    checks = workbook.add_worksheet("Checks")
    checks.write_row(0, 0, ["Check", "State"], header)
    checks.write_row(1, 0, ["Formula injection protection", "PASS"])
    workbook.close()
    path.write_bytes(output.getvalue())
    return {"status": "SUCCEEDED", "report_id": report_id, "path": str(path), "quality": "DEMO DATA", "outputs": ["xlsx"]}


@app.get("/reports/{report_id}/download")
def download_report(report_id: str):
    path = REPORT_ROOT / f"{report_id}.xlsx"
    return FileResponse(path, filename=f"{report_id}.xlsx", media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
