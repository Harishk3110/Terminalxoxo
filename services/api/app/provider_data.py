"""Immutable provider datasets and persisted connection observations."""

import hashlib
import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select

from . import models
from .object_storage import ObjectStorage
from .portfolio_operations import audit
from .price_sources import utc
from .providers.fred import FredProvider
from .providers.market import JsonMarketProvider
from .providers.reference import OpenFigiProvider, SecProvider

NAMES = {
    "fred": "FRED",
    "sec": "SEC EDGAR",
    "openfigi": "OpenFIGI",
    "market": "Market provider",
    "options": "Options provider",
}


def adapters(settings):
    return {
        "fred": FredProvider(settings),
        "sec": SecProvider(settings),
        "openfigi": OpenFigiProvider(settings),
        "market": JsonMarketProvider(settings),
        "options": JsonMarketProvider(settings, "options"),
    }


def connection(session, key, settings):
    if key not in NAMES:
        raise ValueError("Unsupported provider")
    adapter = adapters(settings)[key]
    name = NAMES[key]
    configured = bool(settings.fred_api_key) if key == "fred" else adapter.configured
    row = session.scalar(
        select(models.ProviderConnection).where(models.ProviderConnection.provider_name == name)
    )
    if row is None:
        enabled = getattr(settings, key + "_enabled")
        row = models.ProviderConnection(
            provider_name=name,
            provider_type={
                "fred": "macro",
                "sec": "filings",
                "openfigi": "reference",
                "market": "market",
                "options": "options",
            }[key],
            enabled=enabled,
            configured=configured,
            connection_state="NOT_TESTED"
            if enabled and configured
            else "NOT_CONFIGURED"
            if not configured
            else "DISABLED",
        )
        session.add(row)
        session.flush()
    row.configured, row.capabilities = configured, adapter.capabilities
    if not configured:
        row.connection_state = "NOT_CONFIGURED"
    return row


def provider_payload(session, row, key=None):
    health = session.scalar(
        select(models.ProviderHealthSnapshot)
        .where(models.ProviderHealthSnapshot.provider_name == row.provider_name)
        .order_by(models.ProviderHealthSnapshot.created_at.desc())
        .limit(1)
    )
    limit = session.scalar(
        select(models.ProviderRateLimitState).where(
            models.ProviderRateLimitState.provider_name == row.provider_name
        )
    )
    latest = session.scalar(
        select(models.DatasetVersion)
        .join(models.Dataset)
        .where(models.Dataset.source == row.provider_name)
        .order_by(models.DatasetVersion.created_at.desc())
        .limit(1)
    )
    return {
        "key": key,
        "name": row.provider_name,
        "type": row.provider_type,
        "configured": row.configured,
        "enabled": row.enabled,
        "connection_state": "DEMO" if row.provider_name == "DemoProvider" else row.connection_state,
        "capabilities": row.capabilities or [],
        "last_success": None if row.provider_name == "DemoProvider" else row.last_success,
        "last_failure": row.last_failure,
        "last_error": row.last_error,
        "last_data_sync": row.last_data_sync,
        "data_freshness": "UNAVAILABLE"
        if not row.last_data_sync
        else "STALE"
        if (datetime.now(UTC) - utc(row.last_data_sync)).total_seconds() > 86400
        else "RECENT_SYNC",
        "latency_ms": health.latency_ms if health else None,
        "rate_limit": limit.state if limit else "UNKNOWN",
        "rate_remaining": limit.remaining if limit else None,
        "latest_dataset_version_id": latest.id if latest else None,
    }


def record_result(session, row, *, response=None, error=None, action="test", actor=None):
    now = datetime.now(UTC)
    state = error.state if error else "CONNECTED"
    row.connection_state = state
    row.last_error = str(error)[:250] if error else None
    if error:
        row.last_failure = now
    else:
        row.last_success = now
    session.add(
        models.ProviderHealthSnapshot(
            provider_name=row.provider_name,
            state=state,
            latency_ms=response.latency_ms if response else None,
            error_message=row.last_error,
        )
    )
    session.add(
        models.ProviderRequestLog(
            provider_name=row.provider_name,
            endpoint=action,
            status_code=error.status_code if error else 200,
            latency_ms=response.latency_ms if response else None,
            correlation_id=str(uuid.uuid4()),
            error_message=row.last_error,
        )
    )
    limit = session.scalar(
        select(models.ProviderRateLimitState).where(
            models.ProviderRateLimitState.provider_name == row.provider_name
        )
    )
    if limit is None:
        limit = models.ProviderRateLimitState(provider_name=row.provider_name)
        session.add(limit)
    remaining = response.rate_remaining if response else None
    limit.remaining = int(remaining) if remaining and remaining.isdigit() else None
    limit.state = (
        "RATE_LIMITED"
        if state == "RATE_LIMITED"
        else "OBSERVED"
        if remaining is not None
        else "UNKNOWN"
    )
    audit(
        session,
        "PROVIDER_" + action.upper(),
        "provider_connection",
        row.id,
        {"state": state},
        actor,
    )
    session.flush()


def persist_dataset(session, response, rows, *, provider, name, kind, request, actor):
    raw_hash = hashlib.sha256(response.content).hexdigest()
    dataset = session.scalar(
        select(models.Dataset).where(
            models.Dataset.name == name,
            models.Dataset.source == provider,
            models.Dataset.dataset_type == kind,
        )
    )
    if dataset is None:
        dataset = models.Dataset(
            name=name, source=provider, dataset_type=kind, quality="PROVIDER DATA"
        )
        session.add(dataset)
        session.flush()
    latest = session.scalar(
        select(models.DatasetVersion)
        .where(models.DatasetVersion.dataset_id == dataset.id)
        .order_by(models.DatasetVersion.version.desc())
        .limit(1)
    )
    if latest and latest.content_hash == raw_hash:
        return latest, False
    number = (
        session.scalar(
            select(func.max(models.DatasetVersion.version)).where(
                models.DatasetVersion.dataset_id == dataset.id
            )
        )
        or 0
    ) + 1
    storage = ObjectStorage()
    root = f"providers/{dataset.id}/{uuid.uuid4()}"
    raw_key = root + "/raw.json"
    storage.put_bytes(key=raw_key, data=response.content, content_type="application/json")
    raw = models.RawObject(
        provider=provider,
        dataset=kind,
        object_key=raw_key,
        content_hash=raw_hash,
        content_type="application/json",
        size_bytes=len(response.content),
        source_uri=response.url,
        correlation_id=str(uuid.uuid4()),
    )
    session.add(raw)
    session.flush()
    curated = json.dumps(rows, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()
    curated_key = root + "/curated.json"
    storage.put_bytes(key=curated_key, data=curated, content_type="application/json")
    version = models.DatasetVersion(
        dataset_id=dataset.id,
        version=number,
        raw_object_id=raw.id,
        row_count=len(rows),
        content_hash=raw_hash,
        schema_json={
            "curated_key": curated_key,
            "curated_hash": hashlib.sha256(curated).hexdigest(),
            "source": provider,
            "quality": "PROVIDER DATA",
            "request": request,
            "ingested_at": datetime.now(UTC).isoformat(),
            "columns": list(rows[0]) if rows else [],
            "point_in_time": "UNVERIFIED",
        },
    )
    session.add(version)
    session.flush()
    session.add(
        models.DatasetLineage(
            dataset_version_id=version.id,
            source_type="PROVIDER_RESPONSE",
            source_id=raw.id,
            transform="Validated read-only response; no portfolio transactions",
        )
    )
    audit(
        session,
        "PROVIDER_DATA_IMPORTED",
        "dataset_version",
        version.id,
        {"provider": provider, "hash": raw_hash, "rows": len(rows), "request": request},
        actor,
    )
    return version, True
