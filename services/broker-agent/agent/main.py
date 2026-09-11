"""Retired inbound demo bridge; the supported paper reader is outbound-only."""

from fastapi import FastAPI, HTTPException, Response

app = FastAPI(title="KnK Retired Broker Bridge", version="0.2.0", docs_url=None, redoc_url=None)


@app.get("/health/live")
def live() -> dict[str, str | bool]:
    return {"status": "live", "service": "retired-broker-bridge", "read_only": True}


@app.get("/health/ready")
def ready() -> None:
    raise HTTPException(503, "Retired demo bridge; no broker connection or synchronization")


@app.get("/metrics")
def metrics() -> Response:
    return Response(
        "# HELP knk_broker_legacy_disabled Retired bridge is disabled.\n"
        "# TYPE knk_broker_legacy_disabled gauge\nknk_broker_legacy_disabled 1\n",
        media_type="text/plain; version=0.0.4",
    )


@app.get("/status")
def status() -> dict[str, str | bool]:
    return {
        "state": "DISABLED",
        "read_only": True,
        "paired": False,
        "source": "UNAVAILABLE",
    }


@app.post("/pair")
def pair() -> None:
    raise HTTPException(
        410,
        "Demo pairing retired; use authenticated terminal agent pairing and the outbound reader",
    )


@app.get("/snapshots/account")
def account_snapshot() -> None:
    raise HTTPException(503, "No broker snapshot available from the retired bridge")
