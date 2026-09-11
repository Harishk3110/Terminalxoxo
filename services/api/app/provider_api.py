"""Private provider controls and reviewed data ingestion; credentials stay server-side."""

import hashlib
import json
from datetime import UTC, date, datetime
from typing import Literal, TypedDict

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue
from sqlalchemy import select

from . import models
from .config import get_settings
from .portfolio_api import identity
from .portfolio_operations import audit
from .portfolio_resource_api import Database
from .provider_data import (
    NAMES,
    ProviderPayload,
    adapters,
    connection,
    persist_dataset,
    provider_key,
    provider_payload,
    record_result,
)
from .providers.http import ProviderError
from .providers.market import PriceObservation
from .providers.reference import MappingJob, cik_value, filing_rows
from .quant_data import dataset_rows
from .terminal_analytics import instrument

router = APIRouter(prefix="/api/v1/connections", tags=["private-providers"])


def require_enabled(row: models.ProviderConnection) -> None:
    if not row.enabled or row.connection_state == "REVOKED":
        raise ValueError("Provider is disabled or locally revoked")
    if not row.configured:
        raise ValueError("Server-side provider configuration is required")


class ConnectionsResponse(TypedDict):
    items: list[ProviderPayload]


class ControlResponse(ProviderPayload):
    revocation_scope: str


@router.get("")
def list_connections(session: Database) -> ConnectionsResponse:
    result = [
        provider_payload(session, connection(session, key, get_settings()), key) for key in NAMES
    ]
    existing = session.scalars(
        select(models.ProviderConnection).where(
            models.ProviderConnection.provider_name.not_in(list(NAMES.values()))
        )
    ).all()
    result.extend(provider_payload(session, row) for row in existing)
    return {"items": result}


class Control(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["ENABLE", "DISABLE", "REVOKE"]


@router.post("/{key}/control")
def control(key: str, payload: Control, request: Request, session: Database) -> ControlResponse:
    actor = identity(request, session, admin=True)
    row = connection(session, key, get_settings())
    if payload.action == "ENABLE" and not row.configured:
        raise ValueError("Configure the provider on the server before enabling it")
    row.enabled = payload.action == "ENABLE"
    row.connection_state = (
        "NOT_TESTED" if row.enabled else "REVOKED" if payload.action == "REVOKE" else "DISABLED"
    )
    audit(
        session,
        "PROVIDER_" + payload.action,
        "provider_connection",
        row.id,
        {"enabled": row.enabled, "scope": "LOCAL_ACCESS_ONLY"},
        actor,
    )
    return {
        **provider_payload(session, row, key),
        "revocation_scope": "LOCAL_ACCESS_ONLY; rotate vendor keys separately",
    }


@router.post("/{key}/test")
async def test_connection(key: str, request: Request, session: Database) -> ProviderPayload:
    actor = identity(request, session, admin=True)
    row = connection(session, key, get_settings())
    require_enabled(row)
    adapter = adapters(get_settings())[provider_key(key)]
    from .provider_probe import probe

    return await probe(
        session, row, key, adapter, actor, request.headers.get("x-correlation-id", "provider-test")
    )


class SecImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cik: str = Field(pattern=r"^[0-9]{1,10}$")
    kind: Literal["submissions", "company_facts"] = "submissions"


def fact_rows(payload: JsonValue) -> list[dict[str, JsonValue]]:
    if not isinstance(payload, dict):
        raise ProviderError("SEC company facts response must be an object")
    facts = payload.get("facts")
    if not isinstance(facts, dict):
        raise ProviderError("SEC company facts object is missing")
    rows: list[dict[str, JsonValue]] = []
    for taxonomy, concepts in facts.items():
        if not isinstance(concepts, dict):
            raise ProviderError("SEC company facts taxonomy must contain named concepts")
        for concept, values in concepts.items():
            if not isinstance(values, dict) or not isinstance(values.get("units"), dict):
                raise ProviderError("SEC company facts concept requires named units")
            units = values["units"]
            if not isinstance(units, dict):
                raise ProviderError("SEC company facts units must be an object")
            label = values.get("label")
            if label is not None and not isinstance(label, str):
                raise ProviderError("SEC company facts label must be text")
            for unit, observations in units.items():
                if not isinstance(observations, list):
                    raise ProviderError("SEC company facts observations must be an array")
                for observation in observations:
                    if not isinstance(observation, dict):
                        raise ProviderError("SEC company facts observation must be an object")
                    rows.append(
                        {
                            **observation,
                            "taxonomy": taxonomy,
                            "concept": concept,
                            "label": label,
                            "unit": unit,
                        }
                    )
                    if len(rows) > 100000:
                        raise ProviderError(
                            "SEC facts exceed 100,000 observations; use a narrower source file"
                        )
    return rows


@router.post("/sec/import")
async def import_sec(
    payload: SecImport, request: Request, session: Database
) -> dict[str, JsonValue]:
    actor = identity(request, session)
    row = connection(session, "sec", get_settings())
    require_enabled(row)
    nested = session.begin_nested()
    try:
        response = await adapters(get_settings())["sec"].read(payload.cik, payload.kind)
        rows: list[dict[str, JsonValue]] = (
            [
                {
                    "cik": filing["cik"],
                    "accession": filing["accession"],
                    "filing_date": filing["filing_date"],
                    "form": filing["form"],
                    "document": filing["document"],
                    "url": filing["url"],
                }
                for filing in filing_rows(response.payload)
            ]
            if payload.kind == "submissions"
            else fact_rows(response.payload)
        )
        filings_object = (
            response.payload.get("filings") if isinstance(response.payload, dict) else None
        )
        historical_files = (
            filings_object.get("files", []) if isinstance(filings_object, dict) else []
        )
        if not isinstance(historical_files, list) or any(
            not isinstance(item, dict) for item in historical_files
        ):
            raise ProviderError("SEC historical filing references must be an array of objects")
        version, created = persist_dataset(
            session,
            response,
            rows,
            provider=row.provider_name,
            name=f"SEC {cik_value(payload.cik)} {payload.kind}",
            kind="sec_filings" if payload.kind == "submissions" else "sec_facts",
            request=payload.model_dump(),
            actor=actor,
        )
        record_result(session, row, response=response, action="sync", actor=actor)
        row.last_data_sync = datetime.now(UTC)
        nested.commit()
        return {
            "state": "IMPORTED" if created else "UNCHANGED",
            "dataset_version_id": version.id,
            "rows": len(rows),
            "source": row.provider_name,
            "scope": "RECENT_FILINGS"
            if payload.kind == "submissions"
            else "RAW_XBRL_FACTS_NOT_CURATED_FINANCIALS",
            "historical_files": historical_files,
        }
    except (ProviderError, ValueError, TypeError, KeyError, OSError) as exc:
        nested.rollback()
        error = (
            exc
            if isinstance(exc, ProviderError)
            else ProviderError("SEC response validation failed")
        )
        record_result(session, row, error=error, action="sync", actor=actor)
        return {"state": error.state, "error": str(error)}


@router.get("/sec/filings")
def filings(session: Database, cik: str | None = None) -> dict[str, JsonValue]:
    versions = session.scalars(
        select(models.DatasetVersion)
        .join(models.Dataset)
        .where(models.Dataset.dataset_type == "sec_filings")
        .order_by(models.DatasetVersion.created_at.desc())
    ).all()
    selected = cik_value(cik) if cik else None
    seen: set[str] = set()
    items: list[dict[str, JsonValue]] = []
    for version in versions:
        rows, provenance = dataset_rows(session, version.id)
        for row in rows:
            accession = row.get("accession")
            if not isinstance(accession, str) or not isinstance(row.get("filing_date"), str):
                raise ProviderError("Persisted filing requires accession and filing date text")
            if (not selected or row["cik"] == selected) and accession not in seen:
                seen.add(accession)
                items.append(
                    {
                        **row,
                        "dataset_version_id": version.id,
                        "source": provenance["source"],
                        "ingested_at": version.created_at.isoformat(),
                    }
                )
    return {
        "items": [
            item for item in sorted(items, key=lambda r: str(r["filing_date"]), reverse=True)[:2000]
        ]
    }


class MapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    jobs: list[MappingJob] = Field(min_length=1, max_length=100)


@router.post("/openfigi/mapping")
async def map_figi(
    payload: MapRequest, request: Request, session: Database
) -> dict[str, JsonValue]:
    actor = identity(request, session)
    row = connection(session, "openfigi", get_settings())
    require_enabled(row)
    jobs = [job.model_dump(exclude_none=True) for job in payload.jobs]
    nested = session.begin_nested()
    try:
        response = await adapters(get_settings())["openfigi"].mapping(jobs)
        if not isinstance(response.payload, list):
            raise ProviderError("OpenFIGI response must be an array")
        rows: list[dict[str, JsonValue]] = [
            {"request": job, "result": result}
            for job, result in zip(jobs, response.payload, strict=True)
        ]
        request_hash = hashlib.sha256(json.dumps(jobs, sort_keys=True).encode()).hexdigest()
        version, _ = persist_dataset(
            session,
            response,
            rows,
            provider=row.provider_name,
            name="OpenFIGI mapping " + request_hash,
            kind="reference_mapping",
            request={"jobs": [job for job in jobs]},
            actor=actor,
        )
        record_result(session, row, response=response, action="mapping", actor=actor)
        row.last_data_sync = datetime.now(UTC)
        nested.commit()
        return {
            "state": "REVIEW_REQUIRED",
            "dataset_version_id": version.id,
            "items": [item for item in rows],
        }
    except (ProviderError, ValueError, OSError) as exc:
        nested.rollback()
        error = (
            exc
            if isinstance(exc, ProviderError)
            else ProviderError("OpenFIGI request or response validation failed")
        )
        record_result(session, row, error=error, action="mapping", actor=actor)
        return {"state": error.state, "error": str(error)}


class AcceptMapping(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_version_id: str
    job_index: int = Field(ge=0, le=99)
    figi: str = Field(pattern=r"^BBG[A-Z0-9]{9}$")
    instrument_id: str
    confirm: bool = False


@router.post("/openfigi/accept")
def accept_mapping(
    payload: AcceptMapping, request: Request, session: Database
) -> dict[str, JsonValue]:
    actor = identity(request, session, admin=True)
    if not payload.confirm:
        raise ValueError("Explicit mapping approval is required")
    rows, provenance = dataset_rows(session, payload.dataset_version_id)
    if provenance["source"] != "OpenFIGI" or payload.job_index >= len(rows):
        raise ValueError("Select an OpenFIGI result from a persisted mapping dataset")
    result = rows[payload.job_index].get("result")
    candidates = result.get("data", []) if isinstance(result, dict) else None
    if not isinstance(candidates, list):
        raise ValueError("Persisted OpenFIGI result requires a candidate array")
    if any(not isinstance(candidate, dict) for candidate in candidates):
        raise ValueError("Persisted OpenFIGI candidate must be an object")
    selected = next(
        (row for row in candidates if isinstance(row, dict) and row.get("figi") == payload.figi),
        None,
    )
    held = session.get(models.Instrument, payload.instrument_id)
    if selected is None or held is None:
        raise ValueError("Instrument or mapping candidate not found")
    if held.figi and held.figi != payload.figi:
        raise ValueError("Existing FIGI conflicts; review the security master before changing it")
    existing = session.scalar(
        select(models.InstrumentIdentifier).where(
            models.InstrumentIdentifier.identifier_type == "FIGI",
            models.InstrumentIdentifier.identifier_value == payload.figi,
            models.InstrumentIdentifier.provider == "OpenFIGI",
        )
    )
    if existing and existing.instrument_id != held.id:
        raise ValueError("FIGI is already assigned to another instrument")
    if not existing:
        session.add(
            models.InstrumentIdentifier(
                instrument_id=held.id,
                identifier_type="FIGI",
                identifier_value=payload.figi,
                provider="OpenFIGI",
            )
        )
    held.figi = payload.figi
    audit(
        session,
        "OPENFIGI_MAPPING_APPROVED",
        "instrument",
        held.id,
        {"figi": payload.figi, "version_id": payload.dataset_version_id, "candidate": selected},
        actor,
    )
    return {"state": "APPROVED", "instrument_id": held.id, "figi": held.figi}


class MarketImport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=40)
    start: date | None = None
    end: date | None = None


@router.post("/{key}/backfill")
async def market_backfill(
    key: Literal["market", "options"], payload: MarketImport, request: Request, session: Database
) -> dict[str, JsonValue]:
    actor = identity(request, session)
    row = connection(session, key, get_settings())
    require_enabled(row)
    security = instrument(session, payload.symbol)
    if payload.start and payload.end and payload.start > payload.end:
        raise ValueError("Start must not be after end")
    nested = session.begin_nested()
    try:
        response, rows = await adapters(get_settings())[key].read(
            security.symbol, payload.start, payload.end
        )
        if any(record["currency"] != security.currency for record in rows):
            raise ProviderError("Provider currency conflicts with security master")
        version, created = persist_dataset(
            session,
            response,
            rows,
            provider=row.provider_name,
            name=f"{row.provider_name} {security.symbol}",
            kind="ohlcv" if key == "market" else "options_chain",
            request=payload.model_dump(mode="json"),
            actor=actor,
        )
        if key == "market" and created:
            for record in rows:
                # The adapter adds a date alias after validating the vendor contract.
                bar = PriceObservation.model_validate(
                    {name: value for name, value in record.items() if name != "date"}
                )
                session.add(
                    models.MarketObservation(
                        instrument_id=security.id,
                        timestamp=bar.timestamp,
                        price=bar.close,
                        currency=bar.currency,
                        source=row.provider_name,
                        source_category="PROVIDER",
                        data_state=bar.data_state,
                        dataset_version_id=version.id,
                        adjustment_state=bar.adjustment_state,
                        fields={**record, "date": bar.timestamp.date().isoformat()},
                    )
                )
        record_result(session, row, response=response, action="sync", actor=actor)
        row.last_data_sync = datetime.now(UTC)
        nested.commit()
        return {
            "state": "IMPORTED" if created else "UNCHANGED",
            "dataset_version_id": version.id,
            "rows": len(rows),
        }
    except (ProviderError, ValueError, TypeError, OSError) as exc:
        nested.rollback()
        error = (
            exc
            if isinstance(exc, ProviderError)
            else ProviderError("Provider data validation failed")
        )
        record_result(session, row, error=error, action="sync", actor=actor)
        return {"state": error.state, "error": str(error)}
