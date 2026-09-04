from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pyotp
import structlog
from argon2 import PasswordHasher
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from . import models
from .config import get_settings
from .database import SessionLocal, engine, get_session
from .providers.fred import FredProvider
from .repositories import InstrumentRepository, JobRepository, ProviderRepository, StrategyRepository, SystemRepository
from .services import BacktestService, DatasetService, DemoIngestionService, FredIngestionService, MacroService, PerformanceService, PineService, PortfolioService, ReportService, RiskService, to_jsonable

try:
    import redis
except Exception:  # pragma: no cover
    redis = None


settings = get_settings()
logger = structlog.get_logger()
hasher = PasswordHasher()

REQUEST_COUNT = Counter("knk_api_requests_total", "Total API requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("knk_api_request_seconds", "API request latency", ["method", "path"])
JOB_COUNT = Gauge("knk_jobs_by_state", "Jobs by state", ["state"])
DATA_RECORDS_INGESTED = Counter("knk_data_records_ingested_total", "Data records ingested", ["provider", "dataset"])
AUTH_FAILURES = Counter("knk_auth_failures_total", "Authentication failures")

app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    docs_url="/docs" if settings.knk_env != "production-paper" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Correlation-ID"],
)

_DB_READY = False


class AdminSetupRequest(BaseModel):
    email: str
    password: str = Field(min_length=12)


class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: str | None = None


class TransactionRequest(BaseModel):
    transaction_type: str
    trade_date: str
    symbol: str | None = None
    quantity: Decimal = Decimal("0")
    price: Decimal = Decimal("0")
    currency: str = "SGD"
    fx_rate_to_base: Decimal = Decimal("1")
    fee: Decimal = Decimal("0")
    notes: str | None = None


class BackfillRequest(BaseModel):
    series_ids: list[str] = Field(default_factory=lambda: ["FEDFUNDS", "DGS2", "DGS10", "CPIAUCSL", "UNRATE"])
    observation_start: str | None = "2016-01-01"


def correlation_id(request: Request) -> str:
    return request.headers.get("X-Correlation-ID") or str(uuid.uuid4())


@app.on_event("startup")
def startup() -> None:
    ensure_database_ready()
    logger.info("api_started", environment=settings.knk_env)


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    ensure_database_ready()
    start = datetime.now(timezone.utc)
    cid = correlation_id(request)
    response = await call_next(request)
    elapsed = (datetime.now(timezone.utc) - start).total_seconds()
    REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
    response.headers["X-Correlation-ID"] = cid
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    if settings.knk_env == "production-paper":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def ensure_database_ready() -> None:
    global _DB_READY
    if _DB_READY:
        return
    models.Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        if not session.execute(select(models.Instrument.id).limit(1)).first():
            DemoIngestionService(session).seed(reset=False)
    _DB_READY = True


def redis_client():
    if redis is None:
        return None
    try:
        return redis.Redis.from_url(settings.redis_url, socket_timeout=1)
    except Exception:
        return None


def enqueue_job(job_id: str) -> bool:
    client = redis_client()
    if client is None:
        return False
    try:
        client.lpush("knk:jobs", job_id)
        return True
    except Exception:
        return False


def require_seeded(session: Session) -> None:
    if not session.execute(select(models.Instrument.id).limit(1)).first():
        DemoIngestionService(session).seed(reset=False)


@app.get("/health/live")
def live():
    return {"status": "live", "environment": settings.knk_env}


@app.get("/health/ready")
def ready(session: Session = Depends(get_session)):
    checks: dict[str, Any] = {"api": "ready"}
    try:
        session.execute(text("select 1"))
        checks["database"] = "ready"
    except Exception as exc:  # noqa: BLE001
        checks["database"] = f"failed: {exc.__class__.__name__}"
    client = redis_client()
    if client is None:
        checks["redis"] = "unavailable"
    else:
        try:
            client.ping()
            checks["redis"] = "ready"
        except Exception as exc:  # noqa: BLE001
            checks["redis"] = f"failed: {exc.__class__.__name__}"
    checks["object_storage"] = "local-ready"
    status = "ready" if checks.get("database") == "ready" else "not-ready"
    return {"status": status, "checks": checks}


@app.get("/metrics")
def metrics(session: Session = Depends(get_session)):
    counts = {row[0]: row[1] for row in session.execute(select(models.IngestionJob.status, func.count()).group_by(models.IngestionJob.status)).all()} if session.bind else {}
    for state, count in counts.items():
        JOB_COUNT.labels(state).set(count)
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/v1/environment")
def environment():
    return {
        "application": settings.app_name,
        "brand": "KnK Capital",
        "environment": settings.knk_env,
        "timezone": settings.knk_timezone,
        "base_currency": settings.knk_base_currency,
        "reference_capital": settings.knk_reference_capital,
        "badges": ["DEMO DATA", "PAPER", "CALCULATED"],
        "paper_only": True,
        "api_version": "v1",
    }


@app.post("/api/v1/auth/setup")
def setup_admin(payload: AdminSetupRequest, response: Response, request: Request, session: Session = Depends(get_session)):
    existing = session.execute(select(models.User).limit(1)).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Administrator already configured")
    user = models.User(email=payload.email, password_hash=hasher.hash(payload.password), role="ADMIN")
    session.add(user)
    session.flush()
    secret = pyotp.random_base32()
    session.add(models.TotpSetting(user_id=user.id, secret_encrypted=f"local-demo:{secret}", enabled=False))
    for code in ["KNK-DEMO-1001", "KNK-DEMO-1002", "KNK-DEMO-1003"]:
        session.add(models.RecoveryCode(user_id=user.id, code_hash=hasher.hash(code)))
    session.add(models.AuditLog(actor_user_id=user.id, action="auth.setup", resource_type="user", resource_id=user.id, correlation_id=correlation_id(request), metadata_json={"email": payload.email}))
    session.commit()
    response.set_cookie("knk_setup", "complete", httponly=True, samesite="strict", secure=settings.knk_env == "production-paper")
    return {"status": "configured", "totp_secret": secret, "recovery_codes": ["KNK-DEMO-1001", "KNK-DEMO-1002", "KNK-DEMO-1003"]}


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, response: Response, request: Request, session: Session = Depends(get_session)):
    user = session.execute(select(models.User).where(models.User.email == payload.email)).scalars().first()
    if not user:
        AUTH_FAILURES.inc()
        session.add(models.LoginAttempt(email=payload.email, success=False, failure_reason="unknown_user", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent")))
        session.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    try:
        hasher.verify(user.password_hash, payload.password)
    except Exception as exc:  # noqa: BLE001
        AUTH_FAILURES.inc()
        session.add(models.LoginAttempt(email=payload.email, success=False, failure_reason="password", ip_address=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent")))
        session.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc
    totp = session.execute(select(models.TotpSetting).where(models.TotpSetting.user_id == user.id)).scalars().first()
    if payload.totp_code and totp:
        secret = totp.secret_encrypted.removeprefix("local-demo:")
        if not pyotp.TOTP(secret).verify(payload.totp_code):
            AUTH_FAILURES.inc()
            raise HTTPException(status_code=401, detail="Invalid TOTP code")
    session_id = str(uuid.uuid4())
    session.add(models.UserSession(user_id=user.id, session_hash=hasher.hash(session_id), expires_at=datetime.now(timezone.utc) + timedelta(hours=8)))
    session.add(models.LoginAttempt(email=payload.email, success=True, ip_address=request.client.host if request.client else None, user_agent=request.headers.get("User-Agent")))
    session.commit()
    response.set_cookie("knk_session", session_id, httponly=True, samesite="strict", secure=settings.knk_env == "production-paper")
    return {"status": "authenticated", "expires_in_seconds": 28800}


@app.get("/api/v1/public/content")
def public_content(session: Session = Depends(get_session)):
    rows = session.execute(select(models.ResearchNote).where(models.ResearchNote.visibility == "PUBLIC")).scalars().all()
    return {"items": [{"id": row.id, "title": row.title, "summary": row.body[:240], "visibility": row.visibility} for row in rows], "allowed_models": ["public_content", "public_products", "public_disclosures", "public_assets"]}


@app.get("/api/v1/functions")
def functions():
    return {
        "items": [
            {"code": "MACRO", "title": "Macro Dashboard", "route": "/macro", "status": "AVAILABLE"},
            {"code": "PORT", "title": "Portfolio", "route": "/portfolio", "status": "AVAILABLE"},
            {"code": "RISK", "title": "Risk", "route": "/risk", "status": "AVAILABLE"},
            {"code": "HEDGE", "title": "Hedge", "route": "/hedge", "status": "AVAILABLE"},
            {"code": "BT", "title": "Backtests", "route": "/backtests", "status": "AVAILABLE"},
            {"code": "DROP", "title": "Data Drop", "route": "/data-drop", "status": "AVAILABLE"},
            {"code": "PINE", "title": "TradingView Pine Export", "route": "/tradingview", "status": "AVAILABLE"},
        ]
    }


@app.get("/api/v1/search")
def search(q: str = "", session: Session = Depends(get_session)):
    instruments = InstrumentRepository(session).list(query=q, limit=20)
    function_items = [item for item in functions()["items"] if q.lower() in (item["code"] + item["title"]).lower()]
    return {"instruments": [to_jsonable({"id": item.id, "symbol": item.symbol, "name": item.name, "asset_class": item.asset_class, "currency": item.currency}) for item in instruments], "functions": function_items}


@app.get("/api/v1/instruments")
def instruments(q: str | None = None, limit: int = 100, offset: int = 0, session: Session = Depends(get_session)):
    require_seeded(session)
    return {"items": [to_jsonable({"id": item.id, "symbol": item.symbol, "name": item.name, "exchange_id": item.exchange_id, "country": item.country, "currency": item.currency, "asset_class": item.asset_class, "security_type": item.security_type, "sector": item.sector, "industry": item.industry, "is_active": item.is_active}) for item in InstrumentRepository(session).list(limit=limit, offset=offset, query=q)]}


@app.get("/api/v1/instruments/{instrument_id}")
def instrument_detail(instrument_id: str, session: Session = Depends(get_session)):
    item = InstrumentRepository(session).get(instrument_id)
    if not item:
        raise HTTPException(status_code=404, detail="Instrument not found")
    return to_jsonable({"id": item.id, "symbol": item.symbol, "name": item.name, "country": item.country, "currency": item.currency, "asset_class": item.asset_class, "security_type": item.security_type, "sector": item.sector, "industry": item.industry, "quality": "DEMO DATA"})


@app.get("/api/v1/providers")
def providers(session: Session = Depends(get_session)):
    return {"items": [to_jsonable({"name": item.provider_name, "type": item.provider_type, "enabled": item.enabled, "configured": item.configured, "connection_state": item.connection_state, "capabilities": item.capabilities, "masked_identifier": item.masked_identifier, "last_success": item.last_success, "last_failure": item.last_failure, "last_error": item.last_error, "last_data_sync": item.last_data_sync, "data_freshness": item.data_freshness}) for item in ProviderRepository(session).list_connections()]}


@app.post("/api/v1/providers/fred/test")
async def fred_test(request: Request, session: Session = Depends(get_session)):
    provider = FredProvider(settings)
    status = await provider.test_connection(correlation_id(request))
    ProviderRepository(session).upsert_connection(provider_name="FRED", provider_type="macro", enabled=settings.fred_enabled, configured=provider.configured, state=status.connection_state.value, capabilities=provider.capabilities, last_error=status.last_error)
    session.commit()
    return to_jsonable(status.__dict__)


@app.get("/api/v1/providers/fred/status")
def fred_status(session: Session = Depends(get_session)):
    provider = session.execute(select(models.ProviderConnection).where(models.ProviderConnection.provider_name == "FRED")).scalars().first()
    if not provider:
        return {"provider_name": "FRED", "configured": False, "enabled": settings.fred_enabled, "connection_state": "NOT_CONFIGURED", "capabilities": FredProvider(settings).capabilities}
    return to_jsonable({"name": provider.provider_name, "type": provider.provider_type, "enabled": provider.enabled, "configured": provider.configured, "connection_state": provider.connection_state, "capabilities": provider.capabilities, "masked_identifier": provider.masked_identifier, "last_success": provider.last_success, "last_failure": provider.last_failure, "last_error": provider.last_error, "last_data_sync": provider.last_data_sync, "data_freshness": provider.data_freshness})


@app.get("/api/v1/macro/series")
def macro_series(q: str | None = None, session: Session = Depends(get_session)):
    return {"items": MacroService(session).series(q)}


@app.get("/api/v1/macro/series/search")
def macro_series_search(q: str, session: Session = Depends(get_session)):
    return {"items": MacroService(session).series(q)}


@app.get("/api/v1/macro/series/{series_id}")
def macro_series_detail(series_id: str, session: Session = Depends(get_session)):
    try:
        return MacroService(session).observations(series_id, limit=5)["series"]
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/macro/series/{series_id}/observations")
def macro_observations(series_id: str, limit: int = 1000, session: Session = Depends(get_session)):
    try:
        return MacroService(session).observations(series_id, limit)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/macro/series/{series_id}/refresh")
async def macro_refresh(series_id: str, request: Request, session: Session = Depends(get_session)):
    cid = correlation_id(request)
    job = JobRepository(session).create(job_type="fred_refresh_series", provider="FRED", parameters={"series_id": series_id}, correlation_id=cid)
    session.commit()
    result = await FredIngestionService(session, FredProvider(settings)).refresh_series(series_id, cid)
    job = JobRepository(session).get(job.id)
    if job:
        JobRepository(session).update(job, status=result["state"] if result["state"] != "NOT_CONFIGURED" else "FAILED", progress=Decimal("1"), records_received=result["records_received"], records_accepted=result["records_accepted"], finished_at=datetime.now(timezone.utc), error_category=None if result["state"] == "SUCCEEDED" else "PROVIDER_NOT_CONFIGURED")
        session.commit()
    DATA_RECORDS_INGESTED.labels("FRED", series_id).inc(result["records_accepted"])
    return {"job_id": job.id if job else None, **result}


@app.post("/api/v1/macro/backfills")
async def macro_backfill(payload: BackfillRequest, request: Request, session: Session = Depends(get_session)):
    cid = correlation_id(request)
    job = JobRepository(session).create(job_type="fred_backfill_series", provider="FRED", parameters=payload.model_dump(), correlation_id=cid)
    session.commit()
    accepted = 0
    received = 0
    states = []
    for series_id in payload.series_ids:
        result = await FredIngestionService(session, FredProvider(settings)).refresh_series(series_id, cid, payload.observation_start)
        states.append({series_id: result["state"]})
        accepted += result["records_accepted"]
        received += result["records_received"]
    job = JobRepository(session).get(job.id)
    if job:
        state = "SUCCEEDED" if accepted else "FAILED"
        JobRepository(session).update(job, status=state, progress=Decimal("1"), records_received=received, records_accepted=accepted, finished_at=datetime.now(timezone.utc), error_category=None if accepted else "PROVIDER_NOT_CONFIGURED")
        session.commit()
    return {"job_id": job.id if job else None, "records_received": received, "records_accepted": accepted, "series_states": states}


@app.get("/api/v1/macro/backfills/{job_id}")
def macro_backfill_job(job_id: str, session: Session = Depends(get_session)):
    job = JobRepository(session).get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return to_jsonable({"id": job.id, "type": job.job_type, "provider": job.provider, "status": job.status, "progress": job.progress, "records_received": job.records_received, "records_accepted": job.records_accepted, "records_rejected": job.records_rejected, "error_category": job.error_category, "error_message": job.error_message})


@app.get("/api/v1/macro/dashboard")
def macro_dashboard(session: Session = Depends(get_session)):
    return MacroService(session).dashboard()


@app.get("/api/v1/portfolios/default")
def portfolio(session: Session = Depends(get_session)):
    return PortfolioService(session).default_snapshot()


@app.post("/api/v1/portfolios/default/transactions")
def add_transaction(payload: TransactionRequest, session: Session = Depends(get_session)):
    try:
        return PortfolioService(session).add_manual_transaction(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/portfolios/default/recalculate")
def recalculate_portfolio(session: Session = Depends(get_session)):
    portfolio_model = session.execute(select(models.Portfolio).where(models.Portfolio.is_default.is_(True))).scalars().first()
    if not portfolio_model:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    result = PortfolioService(session).recalculate(portfolio_model.id)
    session.commit()
    return result


@app.get("/api/v1/performance/default")
def performance(session: Session = Depends(get_session)):
    return PerformanceService(session).latest()


@app.get("/api/v1/risk/default")
def risk(session: Session = Depends(get_session)):
    return RiskService(session).latest()


@app.get("/api/v1/stress/default")
def stress(session: Session = Depends(get_session)):
    return {"items": RiskService(session).stress()}


@app.get("/api/v1/hedge/default")
def hedge(session: Session = Depends(get_session)):
    return RiskService(session).hedge()


@app.get("/api/v1/strategies")
def strategies(session: Session = Depends(get_session)):
    return {"items": [to_jsonable({"id": item.id, "name": item.name, "strategy_type": item.strategy_type, "description": item.description, "status": item.status}) for item in StrategyRepository(session).list_strategies()]}


@app.get("/api/v1/backtests")
def backtests(session: Session = Depends(get_session)):
    return {"items": BacktestService(session).list_runs()}


@app.post("/api/v1/backtests/demo-run")
def run_backtest(session: Session = Depends(get_session)):
    result = BacktestService(session).run_demo_backtest()
    session.commit()
    return result


@app.get("/api/v1/backtests/{run_id}")
def backtest_detail(run_id: str, session: Session = Depends(get_session)):
    try:
        return BacktestService(session).run_payload(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/uploads")
async def upload_dataset(file: UploadFile = File(...), dataset_type: str = "price_bars", session: Session = Depends(get_session)):
    data = await file.read()
    try:
        return DatasetService(session).ingest_bytes(filename=file.filename or "upload.csv", data=data, content_type=file.content_type or "application/octet-stream", dataset_type=dataset_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/datasets")
def datasets(session: Session = Depends(get_session)):
    return {"items": DatasetService(session).list()}


@app.get("/api/v1/jobs")
def jobs(status: str | None = None, session: Session = Depends(get_session)):
    return {"items": [to_jsonable({"id": item.id, "type": item.job_type, "provider": item.provider, "status": item.status, "progress": item.progress, "records_received": item.records_received, "records_accepted": item.records_accepted, "records_rejected": item.records_rejected, "retry_count": item.retry_count, "error_category": item.error_category, "error_message": item.error_message, "created_at": item.created_at, "started_at": item.started_at, "finished_at": item.finished_at}) for item in JobRepository(session).list(status)]}


@app.post("/api/v1/jobs/provider-health-check")
def provider_health_job(request: Request, session: Session = Depends(get_session)):
    job = JobRepository(session).create(job_type="provider_health_check", provider="SYSTEM", parameters={}, correlation_id=correlation_id(request))
    queued = enqueue_job(job.id)
    job.status = "QUEUED" if queued else "PENDING"
    session.commit()
    return {"job_id": job.id, "status": job.status, "redis_enqueued": queued}


@app.post("/api/v1/reports/portfolio-xlsx")
def portfolio_report(session: Session = Depends(get_session)):
    try:
        return ReportService(session).portfolio_xlsx()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc


@app.post("/api/v1/reports/risk-xlsx")
def risk_report(session: Session = Depends(get_session)):
    try:
        return ReportService(session).risk_xlsx()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc


@app.post("/api/v1/reports/backtest-xlsx")
def backtest_report(session: Session = Depends(get_session)):
    try:
        return ReportService(session).backtest_xlsx()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc


@app.post("/api/v1/reports/macro-xlsx")
def macro_report(session: Session = Depends(get_session)):
    try:
        return ReportService(session).macro_xlsx()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Report generation failed: {exc}") from exc


@app.get("/api/v1/reports/{report_id}")
def report_status(report_id: str, session: Session = Depends(get_session)):
    report = ReportService(session).get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@app.get("/api/v1/reports/{report_id}/download")
def report_download(report_id: str, session: Session = Depends(get_session)):
    report = ReportService(session).get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    local_path = report.get("local_path")
    if not local_path:
        raise HTTPException(status_code=404, detail="Report is stored outside this API process")
    return FileResponse(local_path, filename=report["filename"], media_type=report["content_type"])


@app.get("/api/v1/pine/export")
def pine_export(strategy_type: str = "moving_average_crossover"):
    return PineService().generate(strategy_type)


@app.get("/api/v1/alerts")
def alerts(session: Session = Depends(get_session)):
    rows = session.execute(select(models.Alert).order_by(models.Alert.created_at.desc())).scalars().all()
    return {"items": [to_jsonable({"id": row.id, "severity": row.severity, "title": row.title, "message": row.message, "state": row.state, "acknowledged_at": row.acknowledged_at}) for row in rows]}


@app.post("/api/v1/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: str, session: Session = Depends(get_session)):
    alert = session.get(models.Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.state = "RESOLVED"
    alert.acknowledged_at = datetime.now(timezone.utc)
    session.commit()
    return {"status": "acknowledged", "alert_id": alert_id}


@app.get("/api/v1/system/health")
def system_health(session: Session = Depends(get_session)):
    ready_payload = ready(session)
    counts = SystemRepository(session).counts()
    return {
        "environment": settings.knk_env,
        "application_version": "0.2.0",
        "current_commit": "runtime",
        "checks": ready_payload["checks"],
        "provider_state": providers(session)["items"],
        "counts": counts,
        "last_backup": None,
        "last_successful_data_ingestion": to_jsonable(session.execute(select(models.IngestionJob.finished_at).where(models.IngestionJob.status == "SUCCEEDED").order_by(models.IngestionJob.finished_at.desc())).scalars().first()),
    }


# Backward-compatible routes retained for the existing first build clients.
@app.get("/api/environment")
def old_environment():
    return environment()


@app.get("/api/portfolio")
def old_portfolio(session: Session = Depends(get_session)):
    return portfolio(session)


@app.get("/api/risk")
def old_risk(session: Session = Depends(get_session)):
    return risk(session)
