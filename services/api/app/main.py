from __future__ import annotations

import asyncio
import json
import os
import time
from decimal import Decimal
from typing import Any

import pyotp
import structlog
from argon2 import PasswordHasher
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel, Field
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = structlog.get_logger()
hasher = PasswordHasher()

REQUEST_COUNT = Counter("knk_api_requests_total", "Total API requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("knk_api_request_seconds", "API request latency", ["method", "path"])

APP_NAME = os.getenv("APP_NAME", "KnK Capital Terminal")
KNK_ENV = os.getenv("KNK_ENV", "local-demo")
BASE_CURRENCY = os.getenv("KNK_BASE_CURRENCY", "SGD")
REFERENCE_CAPITAL = Decimal(os.getenv("KNK_REFERENCE_CAPITAL", "70000"))

app = FastAPI(
    title=APP_NAME,
    version="0.1.0",
    docs_url="/docs" if KNK_ENV != "production-paper" else None,
    redoc_url=None,
)

allowed_origins = [
    os.getenv("PUBLIC_WEB_ORIGIN", "http://localhost:3000"),
    os.getenv("TERMINAL_WEB_ORIGIN", "http://localhost:3001"),
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token", "X-Correlation-ID"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    path = request.url.path
    REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, path).observe(elapsed)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'"
    if KNK_ENV == "production-paper":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


class Trace(BaseModel):
    provider: str
    dataset: str
    effective_timestamp: str
    ingestion_timestamp: str
    currency: str
    methodology: str
    quality: str


class Position(BaseModel):
    instrument_id: str
    ticker: str
    quantity: Decimal
    average_cost: Decimal
    market_price: Decimal
    market_value: Decimal
    unrealised_pnl: Decimal
    weight: Decimal
    trace: Trace


class AuthSetupRequest(BaseModel):
    email: str
    password: str = Field(min_length=12)


class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: str | None = None


DEMO_TRACE = Trace(
    provider="KnK deterministic fixture",
    dataset="local-demo-fixtures",
    effective_timestamp="2026-09-05T09:00:00+08:00",
    ingestion_timestamp="2026-09-05T09:01:00+08:00",
    currency=BASE_CURRENCY,
    methodology="Deterministic synthetic data for demo workflows only.",
    quality="DEMO DATA",
)

SECURITIES = [
    {
        "id": "sec-aapl-us",
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Information Technology",
        "currency": "USD",
        "last_price": Decimal("231.42"),
        "day_change_percent": Decimal("0.84"),
        "trace": DEMO_TRACE.model_copy(update={"dataset": "demo-equity-prices", "currency": "USD"}),
    },
    {
        "id": "sec-msft-us",
        "ticker": "MSFT",
        "name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "sector": "Information Technology",
        "currency": "USD",
        "last_price": Decimal("418.31"),
        "day_change_percent": Decimal("-0.21"),
        "trace": DEMO_TRACE.model_copy(update={"dataset": "demo-equity-prices", "currency": "USD"}),
    },
]

POSITIONS = [
    Position(
        instrument_id="sec-aapl-us",
        ticker="AAPL",
        quantity=Decimal("55"),
        average_cost=Decimal("218.12"),
        market_price=Decimal("231.42"),
        market_value=Decimal("16972.61"),
        unrealised_pnl=Decimal("974.03"),
        weight=Decimal("0.2374"),
        trace=DEMO_TRACE.model_copy(update={"dataset": "demo-portfolio-positions", "currency": "USD"}),
    ),
    Position(
        instrument_id="sec-msft-us",
        ticker="MSFT",
        quantity=Decimal("34"),
        average_cost=Decimal("402.50"),
        market_price=Decimal("418.31"),
        market_value=Decimal("18932.17"),
        unrealised_pnl=Decimal("716.58"),
        weight=Decimal("0.2648"),
        trace=DEMO_TRACE.model_copy(update={"dataset": "demo-portfolio-positions", "currency": "USD"}),
    ),
]

PUBLIC_CONTENT = [
    {
        "slug": "demo-quality-growth-framework",
        "title": "Quality Growth Framework",
        "summary": "Sanitized public methodology note using only demo data.",
        "status": "published-demo",
    }
]

ADMIN_STATE: dict[str, Any] = {}


def serialize(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [serialize(item) for item in value]
    if isinstance(value, dict):
        return {key: serialize(item) for key, item in value.items()}
    return value


@app.get("/health/live")
def live():
    return {"status": "live", "environment": KNK_ENV}


@app.get("/health/ready")
def ready():
    return {
        "status": "ready",
        "services": {
            "api": "ready",
            "postgres": "configured",
            "redis": "configured",
            "object_storage": "configured",
        },
    }


@app.get("/metrics")
def metrics():
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/api/environment")
def environment():
    return {
        "application": APP_NAME,
        "brand": "KnK Capital",
        "environment": KNK_ENV,
        "timezone": os.getenv("KNK_TIMEZONE", "Asia/Singapore"),
        "base_currency": BASE_CURRENCY,
        "reference_capital": str(REFERENCE_CAPITAL),
        "badges": ["DEMO DATA", "PAPER", "CALCULATED"],
        "paper_only": True,
    }


@app.post("/api/auth/setup")
def setup_admin(payload: AuthSetupRequest):
    if ADMIN_STATE:
        raise HTTPException(status_code=409, detail="Administrator already configured")
    totp_secret = pyotp.random_base32()
    ADMIN_STATE.update(
        {
            "email": payload.email,
            "password_hash": hasher.hash(payload.password),
            "totp_secret": totp_secret,
            "recovery_codes": ["KNK-DEMO-1001", "KNK-DEMO-1002", "KNK-DEMO-1003"],
        }
    )
    logger.info("admin_setup_completed", email=payload.email)
    return {"status": "configured", "totp_secret": totp_secret, "recovery_codes": ADMIN_STATE["recovery_codes"]}


@app.post("/api/auth/login")
def login(payload: LoginRequest):
    if not ADMIN_STATE:
        raise HTTPException(status_code=428, detail="Administrator setup required")
    if payload.email != ADMIN_STATE["email"]:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    try:
        hasher.verify(ADMIN_STATE["password_hash"], payload.password)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=401, detail="Invalid credentials") from exc
    if payload.totp_code and not pyotp.TOTP(ADMIN_STATE["totp_secret"]).verify(payload.totp_code):
        raise HTTPException(status_code=401, detail="Invalid TOTP code")
    return {"status": "authenticated", "session": "demo-session", "same_site": "strict"}


@app.get("/api/public/content")
def public_content():
    return {"items": PUBLIC_CONTENT, "allowed_models": ["public_content", "public_products", "public_disclosures", "public_assets"]}


@app.get("/api/market/securities")
def securities():
    return serialize({"items": SECURITIES, "trace": DEMO_TRACE})


@app.get("/api/market/security/{instrument_id}")
def security(instrument_id: str):
    for item in SECURITIES:
        if item["id"] == instrument_id:
            return serialize(item)
    raise HTTPException(status_code=404, detail="Data unavailable: instrument not found in configured provider")


@app.get("/api/portfolio")
def portfolio():
    nav = sum((position.market_value for position in POSITIONS), Decimal("0")) + Decimal("18420.50")
    return serialize(
        {
            "name": "KnK Capital Reference Portfolio",
            "base_currency": BASE_CURRENCY,
            "reference_capital": REFERENCE_CAPITAL,
            "nav": nav,
            "cash": Decimal("18420.50"),
            "positions": POSITIONS,
            "trace": DEMO_TRACE,
        }
    )


@app.get("/api/risk")
def risk():
    return serialize(
        {
            "beta": Decimal("1.08"),
            "annual_volatility": Decimal("0.183"),
            "value_at_risk_95": Decimal("-2130.42"),
            "conditional_value_at_risk_95": Decimal("-3184.77"),
            "max_drawdown": Decimal("-0.087"),
            "gross_exposure": Decimal("0.689"),
            "net_exposure": Decimal("0.689"),
            "trace": DEMO_TRACE.model_copy(update={"dataset": "demo-risk-calculations", "methodology": "Fixture risk model for local demo."}),
        }
    )


@app.get("/api/options/{instrument_id}")
def options(instrument_id: str):
    if instrument_id not in {item["id"] for item in SECURITIES}:
        raise HTTPException(status_code=404, detail="Data unavailable: options entitlement missing for instrument")
    return serialize(
        {
            "instrument_id": instrument_id,
            "chain": [
                {"strike": Decimal("220"), "call_delta": Decimal("0.67"), "put_delta": Decimal("-0.31"), "implied_volatility": Decimal("0.25"), "gamma_exposure": Decimal("2325000")},
                {"strike": Decimal("230"), "call_delta": Decimal("0.51"), "put_delta": Decimal("-0.48"), "implied_volatility": Decimal("0.24"), "gamma_exposure": Decimal("2910000")},
            ],
            "trace": DEMO_TRACE.model_copy(update={"dataset": "demo-options-chain", "currency": "USD"}),
        }
    )


@app.get("/api/providers")
def providers():
    return {
        "items": [
            {"name": "Mock market provider", "mode": "DEMO", "status": "available", "required_entitlement": None},
            {"name": "Mock fundamentals provider", "mode": "DEMO", "status": "available", "required_entitlement": None},
            {"name": "IBKR paper agent", "mode": "PAPER", "status": "waiting_for_pairing", "required_entitlement": "Local TWS or IB Gateway read-only API"},
        ]
    }


@app.get("/api/broker/status")
def broker_status():
    return {
        "mode": "PAPER",
        "paired": False,
        "read_only": True,
        "heartbeat": None,
        "password_storage": "not supported",
        "local_endpoint_policy": "localhost or trusted local address only",
    }


@app.get("/api/jobs/events")
async def job_events():
    async def event_stream():
        events = [
            {"job": "demo-backfill", "progress": 0.25, "state": "running"},
            {"job": "demo-backfill", "progress": 0.75, "state": "running"},
            {"job": "demo-backfill", "progress": 1.0, "state": "completed"},
        ]
        for event in events:
            yield f"data: {json.dumps(event)}\n\n"
            await asyncio.sleep(0.05)

    return StreamingResponse(event_stream(), media_type="text/event-stream")
