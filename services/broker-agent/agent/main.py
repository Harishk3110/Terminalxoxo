from __future__ import annotations

import os
from datetime import UTC, datetime

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="KnK Read-Only Broker Agent", version="0.1.0")


class PairingRequest(BaseModel):
    device_name: str
    one_time_code: str


@app.get("/health/live")
def live():
    return {"status": "live", "service": "broker-agent", "read_only": True}


@app.get("/metrics")
def metrics():
    return "knk_broker_agent_heartbeat_total 1\n"


@app.get("/status")
def status():
    return {
        "mode": "PAPER",
        "read_only": True,
        "gateway_host": os.getenv("IBKR_GATEWAY_HOST", "127.0.0.1"),
        "gateway_port": os.getenv("IBKR_GATEWAY_PORT", "7497"),
        "paired": False,
        "heartbeat": datetime.now(UTC).isoformat(),
        "credential_storage": "Windows Credential Manager integration point",
    }


@app.post("/pair")
def pair(payload: PairingRequest):
    return {
        "status": "pairing-request-recorded",
        "device_name": payload.device_name,
        "read_only": True,
        "revocable_device_token": "demo-device-token-redacted",
    }


@app.get("/snapshots/account")
def account_snapshot():
    return {
        "mode": "PAPER",
        "quality": "DEMO DATA",
        "net_liquidation_value": "71482.35",
        "base_currency": "SGD",
        "cash_balances": [{"currency": "SGD", "amount": "18420.50"}],
        "positions": [],
    }
