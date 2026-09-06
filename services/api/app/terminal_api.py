from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import subprocess
import sys
import time
import uuid
from zipfile import BadZipFile, ZipFile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from . import models
from .config import get_settings
from .database import get_session
from .object_storage import ObjectStorage
from .services import DatasetService, MacroService, PortfolioService, ReportService, ReportFormula, infer_tabular, to_jsonable
from .terminal_analytics import FUNCTIONS, VERSION, factor_analysis, fundamentals, history, portfolio_analytics, quotes, scenario_library, valuation

router = APIRouter(prefix="/api/v1")


class WorkspaceRequest(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    configuration: dict = Field(default_factory=dict)


class RunRequest(BaseModel):
    kind: str
    name: str = Field(min_length=1, max_length=200)
    parameters: dict = Field(default_factory=dict)


class ImportRequest(BaseModel):
    upload_id: str
    mapping: dict[str, str]
    name: str = Field(min_length=1, max_length=200, pattern=r"^[^/\\]+$")
    licence: str = Field(min_length=1, max_length=1000)


def workspace_payload(row, state):
    return {"id": row.id, "name": row.name, "configuration": state.configuration if state else {}}


@router.get("/workspaces")
def workspaces(session: Session = Depends(get_session)):
    rows = session.scalars(select(models.Workspace).order_by(models.Workspace.created_at)).all()
    if not rows:
        seeds = [("KnK Portfolio", "/overview"), ("Global Macro", "/macro"), ("US Equities", "/security-master"), ("Options", "/functions/opt"), ("Earnings", "/functions/earn"), ("Quant Lab", "/quant"), ("Research", "/research"), ("Risk Monitor", "/stress-tests"), ("Data Operations", "/data-jobs")]
        for name, route in seeds:
            row = models.Workspace(name=name)
            session.add(row)
            session.flush()
            session.add(models.WorkspaceState(workspace_id=row.id, configuration={"tabs": [{"id": str(uuid.uuid4()), "route": route, "title": name}], "securities": ["AAPL"], "inspector": True, "rail": True}))
        session.commit()
        rows = session.scalars(select(models.Workspace).order_by(models.Workspace.created_at)).all()
    states = {r.workspace_id: r for r in session.scalars(select(models.WorkspaceState)).all()}
    return {"items": [workspace_payload(row, states.get(row.id)) for row in rows]}


@router.post("/workspaces")
def create_workspace(payload: WorkspaceRequest, session: Session = Depends(get_session)):
    row = models.Workspace(name=payload.name)
    session.add(row)
    session.flush()
    state = models.WorkspaceState(workspace_id=row.id, configuration=payload.configuration)
    session.add(state)
    session.commit()
    return workspace_payload(row, state)


@router.post("/workspaces/{workspace_id}")
def save_workspace(workspace_id: str, payload: WorkspaceRequest, session: Session = Depends(get_session)):
    row = session.get(models.Workspace, workspace_id)
    if not row:
        raise HTTPException(404, "Workspace not found")
    if len(json.dumps(payload.configuration)) > 200000:
        raise HTTPException(413, "Workspace configuration too large")
    row.name = payload.name
    state = session.scalar(select(models.WorkspaceState).where(models.WorkspaceState.workspace_id == row.id))
    if not state:
        state = models.WorkspaceState(workspace_id=row.id, configuration={})
        session.add(state)
    state.configuration = payload.configuration
    session.commit()
    return workspace_payload(row, state)


@router.post("/workspaces/{workspace_id}/delete")
def delete_workspace(workspace_id: str, session: Session = Depends(get_session)):
    if len(session.scalars(select(models.Workspace.id)).all()) <= 1:
        raise HTTPException(409, "Keep at least one workspace")
    for model in (models.WorkspaceState, models.WorkspaceTab):
        session.execute(delete(model).where(model.workspace_id == workspace_id))
    session.execute(delete(models.Workspace).where(models.Workspace.id == workspace_id))
    session.commit()
    return {"status": "deleted"}


@router.get("/terminal/bootstrap")
def bootstrap(session: Session = Depends(get_session)):
    from .broker_api import snapshot
    broker_state = snapshot(session)["state"]
    return {"functions": FUNCTIONS, "quotes": quotes(session), "workspaces": workspaces(session)["items"], "scenarios": scenario_library(), "timezone": "Asia/Singapore", "currency": "SGD", "broker_mode": "PAPER", "broker_state": broker_state, "calculation_version": VERSION, "as_of": datetime.now(timezone.utc).isoformat()}


@router.get("/quotes")
def quote_list(session: Session = Depends(get_session)):
    return {"items": quotes(session)}


@router.get("/prices/{key}")
def prices(key: str, limit: int = 2600, session: Session = Depends(get_session)):
    try:
        return history(session, key, min(max(2, limit), 10000))
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/terminal/portfolio")
def terminal_portfolio(session: Session = Depends(get_session)):
    return portfolio_analytics(session)


@router.get("/fundamentals/{key}")
def financials(key: str, session: Session = Depends(get_session)):
    try:
        return fundamentals(session, key)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/valuation/{key}")
def dcf(key: str, growth: float = .08, wacc: float = .10, terminal_growth: float = .025, session: Session = Depends(get_session)):
    try:
        return valuation(session, key, growth, wacc, terminal_growth)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/factors")
def factors(lookback: int = 63, session: Session = Depends(get_session)):
    return factor_analysis(session, lookback)


def run_payload(run):
    return {"id": run.id, "kind": run.kind, "name": run.name, "status": run.status, "parameters": {k: v for k, v in run.parameters.items() if not k.startswith("_")}, "result": run.result, "history": run.history, "error": run.error, "created_at": run.created_at.isoformat(), "started_at": run.started_at.isoformat() if run.started_at else None, "finished_at": run.finished_at.isoformat() if run.finished_at else None}


def launch_worker(run_id):
    env = dict(os.environ)
    root = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = str(root)
    url = get_settings().database_url
    if url.startswith("sqlite:///./"):
        url = "sqlite:///" + str(Path(url.removeprefix("sqlite:///./")).resolve()).replace("\\", "/")
    env["DATABASE_URL"] = url
    logs = Path("logs")
    logs.mkdir(exist_ok=True)
    with (logs / f"analysis-{run_id}.log").open("wb") as stream:
        subprocess.Popen([sys.executable, "-m", "app.terminal_worker", run_id], env=env, stdout=stream, stderr=stream, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)


@router.post("/terminal/runs", status_code=202)
def start_run(payload: RunRequest, session: Session = Depends(get_session)):
    if payload.kind not in ("stress", "backtest"):
        raise HTTPException(422, "Unknown analytical template")
    if len(session.scalars(select(models.AnalysisRun.id).where(models.AnalysisRun.status.in_(["QUEUED", "RUNNING"]))).all()) >= 4:
        raise HTTPException(429, "Four analytical jobs are already active")
    params = dict(payload.parameters)
    if payload.kind == "stress":
        from .portfolio_valuation import PortfolioValuationService
        try:
            params["_portfolio"] = PortfolioValuationService(session).latest(params.get("portfolio", "KNK_MAIN"))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
    if payload.kind == "backtest" and params.get("dataset_id"):
        version = session.get(models.DatasetVersion, params["dataset_version_id"]) if params.get("dataset_version_id") else session.scalar(select(models.DatasetVersion).where(models.DatasetVersion.dataset_id == params["dataset_id"]).order_by(models.DatasetVersion.version.desc()))
        if not version or version.dataset_id != params["dataset_id"]:
            raise HTTPException(404, "Dataset version not found")
        params["dataset_version_id"] = version.id
        params["mapping"] = (version.schema_json or {}).get("mapping", {"date": "date", "close": "close"})
        params["suffix"] = (version.schema_json or {}).get("suffix", "csv")
    now = datetime.now(timezone.utc).isoformat()
    run = models.AnalysisRun(kind=payload.kind, name=payload.name, parameters=params, status="QUEUED", history=[{"state": "QUEUED", "at": now, "message": "Immutable inputs stored"}])
    session.add(run)
    session.commit()
    try:
        launch_worker(run.id)
    except OSError as exc:
        run.status, run.error = "FAILED", f"Worker launch failed: {exc.__class__.__name__}"
        session.commit()
    return run_payload(run)


@router.get("/terminal/runs")
def runs(kind: str | None = None, session: Session = Depends(get_session)):
    query = select(models.AnalysisRun).order_by(models.AnalysisRun.created_at.desc()).limit(50)
    if kind:
        query = query.where(models.AnalysisRun.kind == kind)
    return {"items": [run_payload(r) for r in session.scalars(query).all()]}


@router.get("/terminal/runs/{run_id}")
def run_detail(run_id: str, session: Session = Depends(get_session)):
    run = session.get(models.AnalysisRun, run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    return run_payload(run)


@router.post("/terminal/runs/{run_id}/cancel")
def cancel_run(run_id: str, session: Session = Depends(get_session)):
    run = session.get(models.AnalysisRun, run_id)
    if not run or run.status not in ("QUEUED", "RUNNING"):
        raise HTTPException(409, "Run is not active")
    run.status = "CANCELLED"
    run.history = [*run.history, {"state": "CANCELLED", "at": datetime.now(timezone.utc).isoformat(), "message": "Cancellation requested; worker result will be discarded"}]
    session.commit()
    return run_payload(run)


@router.get("/terminal/runs/{run_id}/export")
def export_run(run_id: str, session: Session = Depends(get_session)):
    run = run_detail(run_id, session)
    result = run["result"]
    if not result:
        raise HTTPException(409, "Run has no result")
    rows = result.get("contributions") or result.get("equity_curve") or []
    sheets = {"Run": [["Field", "Value"], ["Run ID", run_id], ["Name", run["name"]], ["Source", result["source"]], ["Data as of", result["as_of"]], ["Quality", result["quality"]]], "Results": [list(rows[0])] + [list(r.values()) for r in rows] if rows else [["No rows"]], "Assumptions": [["Field", "Value"]] + [[k, json.dumps(v)] for k, v in run["parameters"].items()], "Warnings": [[w] for w in result.get("warnings", [])]}
    if run["kind"] == "stress":
        sheets["Summary"] = [["Pre NAV", "Estimated P&L", "Post NAV"], [result["pre_nav"], result["loss"], ReportFormula("=A2+B2", result["post_nav"])]]
    return ReportService(session)._write_workbook("terminal-run", sheets)


@router.post("/uploads/preview")
async def preview_upload(file: UploadFile = File(...), session: Session = Depends(get_session)):
    data = await file.read(25_000_001)
    filename = Path(file.filename or "upload.csv").name
    if len(data) > 25_000_000:
        raise HTTPException(413, "Maximum upload size is 25 MB")
    suffix = Path(filename).suffix.lower().lstrip(".")
    try:
        if suffix == "xlsx":
            from openpyxl import load_workbook
            with ZipFile(io.BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist()) > 100_000_000:
                    raise ValueError("Expanded workbook exceeds 100 MB")
            workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
            values = list(workbook.active.values)
            text_buffer = io.StringIO()
            writer = csv.writer(text_buffer)
            writer.writerows(values)
            data, suffix = text_buffer.getvalue().encode(), "csv"
        rows, columns = infer_tabular(data, suffix)
    except (ValueError, UnicodeError, csv.Error, BadZipFile, KeyError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    if not rows:
        raise HTTPException(422, "No data rows found")
    key = f"uploads/{uuid.uuid4()}/preview.{suffix}"
    stored = ObjectStorage().put_bytes(key=key, data=data, content_type="text/csv" if suffix == "csv" else "application/json")
    upload = models.UploadedFile(original_filename=filename, content_type=suffix, object_key=key, content_hash=stored.content_hash, size_bytes=len(data), upload_state="PREVIEW")
    session.add(upload)
    session.commit()
    return {"upload_id": upload.id, "name": filename, "size": len(data), "hash": stored.content_hash, "columns": columns, "preview": rows[:30], "row_count": len(rows), "missing": sum(v in (None, "") for row in rows for v in row.values()), "duplicates": len(rows) - len({json.dumps(r, sort_keys=True) for r in rows}), "source": "USER_UPLOAD", "quality": "UNVERIFIED", "as_of": upload.created_at.isoformat()}


def validated_upload(payload, session):
    upload = session.get(models.UploadedFile, payload.upload_id)
    if not upload:
        raise HTTPException(404, "Upload not found")
    raw = ObjectStorage().get_bytes(upload.object_key)
    rows, _ = infer_tabular(raw, upload.content_type)
    errors = []
    if not payload.mapping.get("date") or not payload.mapping.get("close"):
        errors.append("Map date and close columns")
    else:
        for i, row in enumerate(rows):
            try:
                datetime.fromisoformat(str(row[payload.mapping["date"]]))
                value = float(row[payload.mapping["close"]])
                if not 0 < value < 1e12:
                    raise ValueError()
            except (KeyError, TypeError, ValueError):
                errors.append(f"Row {i + 1}: invalid date or positive close")
                if len(errors) == 10:
                    break
    return upload, raw, {"valid": not errors, "errors": errors, "row_count": len(rows), "source": "USER_UPLOAD", "point_in_time": "UNVERIFIED"}


@router.post("/uploads/validate")
def validate_upload(payload: ImportRequest, session: Session = Depends(get_session)):
    return validated_upload(payload, session)[2]


@router.post("/uploads/import")
def import_upload(payload: ImportRequest, session: Session = Depends(get_session)):
    upload, raw, result = validated_upload(payload, session)
    if not result["valid"]:
        raise HTTPException(422, result["errors"])
    data = DatasetService(session).ingest_bytes(filename=f"{payload.name}.{upload.content_type}", data=raw, content_type=upload.content_type)
    version = session.get(models.DatasetVersion, data["version_id"])
    version.schema_json = {**version.schema_json, "mapping": payload.mapping, "licence": payload.licence, "suffix": upload.content_type}
    dataset = session.get(models.Dataset, data["dataset_id"])
    dataset.quality = "USER PROVIDED"
    upload.upload_state = "IMPORTED"
    session.commit()
    return {**data, "quality": dataset.quality}


@router.get("/datasets/{dataset_id}")
def dataset_detail(dataset_id: str, session: Session = Depends(get_session)):
    dataset = session.get(models.Dataset, dataset_id)
    if not dataset:
        raise HTTPException(404, "Dataset not found")
    versions = session.scalars(select(models.DatasetVersion).where(models.DatasetVersion.dataset_id == dataset_id).order_by(models.DatasetVersion.version.desc())).all()
    result = []
    for version in versions:
        schema = dict(version.schema_json or {})
        if schema.get("curated_key"):
            content = ObjectStorage().get_bytes(schema["curated_key"])
            if hashlib.sha256(content).hexdigest() != schema["curated_hash"]:
                raise HTTPException(409, "Curated dataset integrity check failed")
            preview = json.loads(content)[:30]
            schema = {**schema, "raw_columns": schema.get("columns"), "preview": preview, "columns": [{"name": k} for k in preview[0]] if preview else []}
        lineage = session.scalars(select(models.DatasetLineage).where(models.DatasetLineage.dataset_version_id == version.id)).all()
        linked = [run_payload(run) for run in session.scalars(select(models.AnalysisRun).where(models.AnalysisRun.kind == "backtest")).all() if run.parameters.get("dataset_version_id") == version.id]
        result.append({"id": version.id, "version": version.version, "rows": version.row_count, "hash": version.content_hash, "schema": schema, "as_of": version.created_at.isoformat(), "lineage": [{"source_type": r.source_type, "source_id": r.source_id, "transform": r.transform} for r in lineage], "backtests": linked})
    return {"id": dataset.id, "name": dataset.name, "source": dataset.source, "quality": dataset.quality, "versions": result}


@router.get("/research")
def research(session: Session = Depends(get_session)):
    return {"items": [{"id": r.id, "title": r.title, "body": r.body, "instrument_id": r.instrument_id, "visibility": r.visibility, "source": "KnK research records", "as_of": r.updated_at.isoformat()} for r in session.scalars(select(models.ResearchNote).order_by(models.ResearchNote.updated_at.desc())).all()]}


class ResearchRequest(BaseModel):
    id: str | None = None
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(max_length=50000)
    instrument_id: str | None = None


@router.post("/research")
def save_research(payload: ResearchRequest, session: Session = Depends(get_session)):
    row = session.get(models.ResearchNote, payload.id) if payload.id else None
    if payload.id and not row:
        raise HTTPException(404, "Research note not found")
    if row is None:
        row = models.ResearchNote(title=payload.title, body=payload.body, instrument_id=payload.instrument_id, visibility="PRIVATE")
        session.add(row)
    else:
        row.title, row.body = payload.title, payload.body
        row.visibility = "PRIVATE"
    session.commit()
    return {"id": row.id, "status": "saved", "visibility": row.visibility}


@router.get("/terminal/health")
def terminal_health(session: Session = Depends(get_session)):
    started = time.perf_counter()
    session.execute(text("select 1"))
    measured = round((time.perf_counter() - started) * 1000, 1)
    now = datetime.now(timezone.utc).isoformat()
    settings = get_settings()
    rows = [{"service": "API", "state": "HEALTHY", "latency_ms": measured, "as_of": now, "detail": "Request handled"}, {"service": "SQLite" if settings.database_url.startswith("sqlite") else "PostgreSQL", "state": "HEALTHY", "latency_ms": measured, "as_of": now, "detail": "SELECT 1 succeeded"}]
    try:
        import redis
        before = time.perf_counter()
        redis.Redis.from_url(settings.redis_url, socket_connect_timeout=.25, socket_timeout=.25).ping()
        rows.append({"service": "Redis", "state": "HEALTHY", "latency_ms": round((time.perf_counter() - before) * 1000, 1), "as_of": now, "detail": "PING succeeded"})
    except Exception:
        rows.append({"service": "Redis", "state": "OFFLINE", "latency_ms": None, "as_of": now, "detail": "PING failed"})
    try:
        storage = ObjectStorage()
        key = "health/probe.txt"
        storage.put_bytes(key=key, data=b"knk-health", content_type="text/plain")
        if storage.get_bytes(key) != b"knk-health":
            raise OSError("Readback mismatch")
        rows.append({"service": "Object storage", "state": "HEALTHY", "as_of": now, "detail": "Write/read probe succeeded"})
    except Exception:
        rows.append({"service": "Object storage", "state": "FAILED", "as_of": now, "detail": "Write/read probe failed"})
    active = session.scalars(select(models.AnalysisRun).where(models.AnalysisRun.status.in_(["QUEUED", "RUNNING"]))).all()
    rows.append({"service": "Analytical workers", "state": "RUNNING" if active else "IDLE", "as_of": now, "detail": f"{len(active)} active persisted jobs; on-demand processes"})
    from .price_sources import utc
    from .portfolio_seed import profile_for
    agent = session.scalar(select(models.LocalAgent).where(models.LocalAgent.revoked_at.is_(None)).order_by(models.LocalAgent.last_seen.desc()).limit(1))
    online = agent and agent.last_seen and (datetime.now(timezone.utc) - utc(agent.last_seen)).total_seconds() < 90
    rows.append({"service": "Local data agent", "state": "ONLINE" if online else "OFFLINE", "as_of": agent.last_seen.isoformat() if agent and agent.last_seen else None, "detail": "Scoped outbound heartbeat" if online else "No current agent heartbeat"})
    profile = profile_for(session)
    nav = session.scalar(select(models.PortfolioValuationRun).where(models.PortfolioValuationRun.portfolio_id == profile.portfolio_id).order_by(models.PortfolioValuationRun.created_at.desc()).limit(1)) if profile else None
    rows.append({"service": "Portfolio NAV", "state": nav.status if nav else "NOT_CALCULATED", "as_of": nav.created_at.isoformat() if nav else None, "detail": nav.payload.get("quality") if nav else "No valuation run"})
    fred = session.scalar(select(models.MacroObservation).where(models.MacroObservation.provider == "FRED").order_by(models.MacroObservation.ingestion_timestamp.desc()).limit(1))
    rows.append({"service": "FRED", "state": "OBSERVED" if fred else "CONFIGURED" if settings.fred_enabled and settings.fred_api_key else "DEMO", "as_of": fred.ingestion_timestamp.isoformat() if fred else None, "detail": "Persisted FRED observation" if fred else "No connected observations"})
    from .broker_api import current_snapshot
    broker, broker_active = current_snapshot(session, profile.portfolio_id) if profile else (None, False)
    rows.append({"service": "IBKR paper agent", "state": "READ_ONLY" if broker_active else "OFFLINE", "as_of": broker.as_of.isoformat() if broker else None, "detail": "Observed paired paper snapshot" if broker else "No broker snapshot received"})
    for name in ("SEC EDGAR", "OpenFIGI", "AI provider", "News provider", "Options provider", "Email alerts", "Telegram", "Sentry", "Backup", "Public web", "Report service", "Workflow orchestrator"):
        rows.append({"service": name, "state": "NOT_VERIFIED", "as_of": now, "detail": "No current heartbeat or configured probe"})
    try:
        commit = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL, timeout=2).decode().strip()
    except Exception:
        commit = os.environ.get("KNK_COMMIT", "unknown")
    return {"items": rows, "as_of": now, "commit": commit, "version": VERSION, "environment": settings.knk_env}


@router.post("/terminal/reports/{kind}")
def terminal_report(kind: str, session: Session = Depends(get_session)):
    service = ReportService(session)
    if kind == "macro":
        return service.macro_xlsx()
    if kind == "backtest":
        run = session.scalar(select(models.AnalysisRun).where(models.AnalysisRun.kind == "backtest", models.AnalysisRun.status == "SUCCEEDED").order_by(models.AnalysisRun.created_at.desc()))
        if not run:
            raise HTTPException(409, "Complete a backtest before exporting")
        return export_run(run.id, session)
    if kind not in {"risk", "portfolio"}:
        raise HTTPException(404, "Unknown report template")
    data = portfolio_analytics(session)
    rows = data["positions"]
    if any(r["market_price"] is None or r["fx_rate"] is None for r in rows):
        return service.portfolio_xlsx()
    rows = [{**r, "fx_rate": float(r["fx_rate"])} for r in rows]
    sheets = {"Sources": [["Source", "Data as of", "Quality"], [data["source"], data["as_of"], data["quality"]]], "Positions": [["Symbol", "Quantity", "Price", "FX", "Calculated value SGD"]] + [[r["symbol"], float(r["quantity"]), float(r["market_price"]), r["fx_rate"], ReportFormula(f"=B{i+2}*C{i+2}*D{i+2}", float(r["quantity"]) * float(r["market_price"]) * r["fx_rate"])] for i, r in enumerate(rows)], "Risk": [["Metric", "Value"]] + [[k, v] for k, v in data["risk"].items()], "Performance": [["Metric", "Value"]] + [[k, v] for k, v in data["performance"].items()], "Warnings": [[w] for w in data["warnings"]]}
    return service._write_workbook(kind, sheets)


@router.get("/auth/session")
def auth_session(request: Request, session: Session = Depends(get_session)):
    from .auth_sessions import find_session
    row = find_session(session, request.cookies.get("knk_session"))
    user = session.get(models.User, row.user_id) if row else None
    if user and user.is_active:
        return {"authenticated": True, "email": user.email, "role": user.role, "setup_required": False}
    return {"authenticated": False, "setup_required": get_settings().knk_env == "local-demo" and session.scalar(select(models.User.id).limit(1)) is None}


@router.post("/auth/logout")
def logout(request: Request, response: Response, session: Session = Depends(get_session)):
    from .auth_sessions import find_session
    row = find_session(session, request.cookies.get("knk_session"))
    if row:
        row.revoked_at = datetime.now(timezone.utc)
        session.commit()
    response.delete_cookie("knk_session")
    return {"status": "signed_out"}
