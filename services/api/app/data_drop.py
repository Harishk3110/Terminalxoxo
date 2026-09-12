"""Durable file inbox, immutable raw objects, approved versioned imports and lineage."""

import hashlib
import json
from collections.abc import Mapping
from copy import deepcopy
from datetime import UTC, datetime, time
from pathlib import Path
from typing import TypedDict

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from . import models
from .data_mapping import filename_metadata, normalize, parse_file, seed_profiles, suggest_mapping
from .object_storage import ObjectStorage
from .portfolio_engine import decimal
from .portfolio_operations import PortfolioLedgerService, audit


class FilePayload(TypedDict):
    id: str
    filename: str
    hash: str
    size_bytes: int
    state: str
    source: str
    agent_id: str | None
    profile_id: str | None
    dataset_version_id: str | None
    duplicate_of: str | None
    metadata: dict[str, JsonValue]
    mapping: dict[str, str]
    validation: dict[str, JsonValue]
    history: list[dict[str, JsonValue]]
    created_at: str | None
    updated_at: str | None


class MappingInputs(BaseModel):
    model_config = ConfigDict(strict=True, allow_inf_nan=False, hide_input_in_errors=True)
    defaults: dict[str, JsonValue] = Field(default_factory=dict)
    symbol_resolution: str | None = None


JSON_OBJECT = TypeAdapter(dict[str, JsonValue], config=ConfigDict(strict=True, allow_inf_nan=False))


FINAL = {"IMPORTED", "ARCHIVED", "DUPLICATE"}
TRANSITIONS = {
    "DETECTED": {"HASHING"},
    "HASHING": {"UPLOADING", "DUPLICATE"},
    "UPLOADING": {"STORED_RAW", "UPLOAD_FAILED"},
    "STORED_RAW": {"PREVIEWING"},
    "PREVIEWING": {"SCHEMA_DETECTED", "QUARANTINED"},
    "SCHEMA_DETECTED": {"MAPPING_REQUIRED"},
    "MAPPING_REQUIRED": {"MAPPED", "REJECTED"},
    "MAPPED": {"VALIDATING"},
    "VALIDATING": {"VALIDATED", "VALIDATED_WITH_WARNINGS", "VALIDATION_FAILED"},
    "VALIDATED": {"AWAITING_APPROVAL"},
    "VALIDATED_WITH_WARNINGS": {"AWAITING_APPROVAL"},
    "VALIDATION_FAILED": {"MAPPED", "REJECTED"},
    "AWAITING_APPROVAL": {"IMPORTING", "MAPPED", "REJECTED"},
    "IMPORTING": {"IMPORTED", "IMPORT_FAILED"},
    "IMPORT_FAILED": {"MAPPED", "REJECTED"},
    "IMPORTED": {"ARCHIVED"},
    "UPLOAD_FAILED": {"UPLOADING", "REJECTED"},
    "QUARANTINED": {"REJECTED"},
}


def transition(row: models.ExternalFile, state: str, message: str = "") -> None:
    if state not in TRANSITIONS.get(row.state, set()):
        raise ValueError(f"Invalid file transition {row.state} -> {state}")
    row.state = state
    row.history = [
        *row.history,
        {"state": state, "at": datetime.now(UTC).isoformat(), "message": message},
    ]


def file_payload(row: models.ExternalFile) -> FilePayload:
    return {
        "id": row.id,
        "filename": row.filename,
        "hash": row.content_hash,
        "size_bytes": row.size_bytes,
        "state": row.state,
        "source": row.source,
        "agent_id": row.agent_id,
        "profile_id": row.profile_id,
        "dataset_version_id": row.dataset_version_id,
        "duplicate_of": row.duplicate_of,
        "metadata": deepcopy(row.metadata_json),
        "mapping": dict(row.mapping),
        "validation": deepcopy(row.validation),
        "history": deepcopy(row.history),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


class DataDropService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.storage = ObjectStorage()

    def get(self, file_id: str) -> models.ExternalFile:
        row = self.session.get(models.ExternalFile, file_id)
        if row is None:
            raise ValueError("File not found")
        return row

    def raw_rows(self, row: models.ExternalFile) -> tuple[list[dict[str, JsonValue]], list[str]]:
        if row.uploaded_file_id is None:
            raise ValueError("Raw file reference is missing")
        uploaded = self.session.get(models.UploadedFile, row.uploaded_file_id)
        if uploaded is None:
            raise ValueError("Raw file reference is missing")
        data = self.storage.get_bytes(uploaded.object_key)
        if hashlib.sha256(data).hexdigest() != row.content_hash:
            raise ValueError("Raw file integrity check failed")
        return parse_file(data, row.filename)

    def receive(
        self,
        filename: str,
        data: bytes,
        *,
        source: str = "EXTERNAL FILE",
        agent_id: str | None = None,
    ) -> FilePayload:
        if not 0 < len(data) <= 25_000_000:
            raise ValueError("File must be nonempty and at most 25 MB")
        filename = Path(filename.replace("\\", "/")).name
        if not filename or len(filename) > 260:
            raise ValueError("Invalid filename")
        digest = hashlib.sha256(data).hexdigest()
        row = models.ExternalFile(
            filename=filename,
            content_hash=digest,
            size_bytes=len(data),
            state="DETECTED",
            source=source,
            agent_id=agent_id,
            history=[{"state": "DETECTED", "at": datetime.now(UTC).isoformat()}],
            metadata_json={},
        )
        self.session.add(row)
        self.session.flush()
        transition(row, "HASHING")
        existing = self.session.scalar(
            select(models.FileHash).where(models.FileHash.content_hash == digest)
        )
        if existing is None:
            try:
                with self.session.begin_nested():
                    self.session.add(models.FileHash(content_hash=digest, file_id=row.id))
                    self.session.flush()
            except IntegrityError:
                existing = self.session.scalar(
                    select(models.FileHash).where(models.FileHash.content_hash == digest)
                )
        failed = self.session.get(models.ExternalFile, existing.file_id) if existing else None
        if failed and failed.state == "UPLOAD_FAILED" and failed.agent_id == agent_id:
            self.session.delete(row)
            row = failed
            audit(self.session, "RAW_UPLOAD_RETRIED", "external_file", row.id, {"hash": digest})
        elif existing:
            row.duplicate_of = existing.file_id
            transition(row, "DUPLICATE", "Byte-identical file already recorded")
            self.session.commit()
            return file_payload(row)
        transition(row, "UPLOADING")
        key = f"data-drop/raw/{row.id}/{digest}{Path(filename).suffix.lower()}"
        try:
            stored = self.storage.put_bytes(
                key=key, data=data, content_type="application/octet-stream"
            )
            uploaded = models.UploadedFile(
                original_filename=filename,
                content_type=Path(filename).suffix.lower().lstrip("."),
                object_key=key,
                content_hash=stored.content_hash,
                size_bytes=len(data),
                upload_state="STORED_RAW",
            )
            self.session.add(uploaded)
            self.session.flush()
            row.uploaded_file_id = uploaded.id
            transition(row, "STORED_RAW")
        except (OSError, ValueError):
            transition(row, "UPLOAD_FAILED", "Object storage write failed")
            self.session.commit()
            return file_payload(row)
        transition(row, "PREVIEWING")
        try:
            rows, columns = parse_file(data, filename)
            seed_profiles(self.session)
            meta = filename_metadata(filename)
            row.metadata_json = {
                **meta,
                "columns": [*columns],
                "preview": [{**record} for record in rows[:30]],
                "row_count": len(rows),
                "licence": None,
                "raw_key": key,
            }
            transition(row, "SCHEMA_DETECTED")
            transition(row, "MAPPING_REQUIRED", "First mapping and import require approval")
        except Exception as exc:
            transition(row, "QUARANTINED", f"Parser rejected file ({type(exc).__name__})")
            row.validation = {"valid": False, "errors": [str(exc)[:500]]}
        audit(
            self.session,
            "EXTERNAL_FILE_RECEIVED",
            "external_file",
            row.id,
            {"hash": digest, "source": source, "agent_id": agent_id},
        )
        self.session.commit()
        return file_payload(row)

    def map_validate(
        self,
        file_id: str,
        profile_id: str,
        mapping: Mapping[str, str] | None = None,
        defaults: Mapping[str, JsonValue] | None = None,
        resolution: str | None = None,
        actor: str | None = None,
    ) -> FilePayload:
        row = self.get(file_id)
        if row.state in FINAL or row.state in {"QUARANTINED", "REJECTED", "UPLOAD_FAILED"}:
            raise ValueError("This file cannot be mapped")
        profile = self.session.get(models.MappingProfile, profile_id)
        if profile is None:
            raise ValueError("Unknown mapping profile")
        rows, columns = self.raw_rows(row)
        chosen = dict(mapping) if mapping is not None else suggest_mapping(columns, profile)
        inputs = MappingInputs.model_validate(
            {
                "defaults": dict(defaults) if defaults is not None else {},
                "symbol_resolution": resolution,
            }
        )
        if any(value not in columns for value in chosen.values() if value):
            raise ValueError("Mapped columns must exist in the raw file")
        transition(row, "MAPPED")
        row.profile_id, row.mapping, row.source = profile.id, chosen, profile.source
        row.metadata_json = {
            **row.metadata_json,
            "defaults": {**inputs.defaults},
            "symbol_resolution": inputs.symbol_resolution,
            "mapping_profile": profile.code,
            "mapping_version": profile.version,
        }
        transition(row, "VALIDATING")
        normalized, validation = normalize(
            rows,
            chosen,
            profile,
            self.session.scalars(select(models.Instrument)).all(),
            row.metadata_json,
            inputs.defaults,
            inputs.symbol_resolution,
        )
        row.validation = JSON_OBJECT.validate_python(validation)
        transition(
            row,
            "VALIDATED_WITH_WARNINGS"
            if validation["valid"] and validation["warnings"]
            else "VALIDATED"
            if validation["valid"]
            else "VALIDATION_FAILED",
        )
        if validation["valid"]:
            transition(row, "AWAITING_APPROVAL")
        row.metadata_json = {
            **row.metadata_json,
            "normalized_preview": [{**record} for record in normalized[:30]],
        }
        audit(
            self.session,
            "FILE_MAPPING_VALIDATED",
            "external_file",
            row.id,
            {
                "profile": profile.code,
                "version": profile.version,
                "mapping": chosen,
                "defaults": defaults or {},
                "resolution": resolution,
                "validation": validation,
            },
            actor,
        )
        self.session.commit()
        return file_payload(row)

    def import_file(
        self,
        file_id: str,
        *,
        name: str,
        licence: str,
        approve: bool,
        portfolio: str = "KNK_MAIN",
        actor: str | None = None,
    ) -> FilePayload:
        row = self.get(file_id)
        if row.state in {"IMPORTED", "ARCHIVED"}:
            return file_payload(row)
        if row.state != "AWAITING_APPROVAL" or not approve:
            raise ValueError("Validated mapping and explicit import approval required")
        if not licence.strip() or not name.strip() or len(name) > 200:
            raise ValueError("Dataset name and licence note are required")
        if row.profile_id is None:
            raise ValueError("Approved mapping profile is missing")
        profile = self.session.get(models.MappingProfile, row.profile_id)
        if profile is None:
            raise ValueError("Approved mapping profile is missing")
        inputs = MappingInputs.model_validate(row.metadata_json)
        rows, columns = self.raw_rows(row)
        normalized, validation = normalize(
            rows,
            row.mapping,
            profile,
            self.session.scalars(select(models.Instrument)).all(),
            row.metadata_json,
            inputs.defaults,
            inputs.symbol_resolution,
        )
        if not validation["valid"]:
            raise ValueError("Revalidation failed")
        transition(row, "IMPORTING")
        try:
            with self.session.begin_nested():
                dataset = self.session.scalar(
                    select(models.Dataset).where(
                        models.Dataset.name == name,
                        models.Dataset.source == profile.source,
                        models.Dataset.dataset_type == profile.dataset_type,
                    )
                )
                if dataset is None:
                    dataset = models.Dataset(
                        name=name,
                        source=profile.source,
                        dataset_type=profile.dataset_type,
                        quality="FILE IMPORT",
                    )
                    self.session.add(dataset)
                    self.session.flush()
                next_version = (
                    self.session.scalar(
                        select(func.max(models.DatasetVersion.version)).where(
                            models.DatasetVersion.dataset_id == dataset.id
                        )
                    )
                    or 0
                ) + 1
                uploaded = self.session.get(models.UploadedFile, row.uploaded_file_id)
                if uploaded is None:
                    raise ValueError("Raw file reference is missing")
                raw = models.RawObject(
                    provider=profile.source,
                    dataset=profile.dataset_type,
                    object_key=uploaded.object_key,
                    content_hash=row.content_hash,
                    content_type=uploaded.content_type,
                    size_bytes=row.size_bytes,
                    source_uri=row.filename,
                    correlation_id=row.id,
                )
                self.session.add(raw)
                self.session.flush()
                normalized.sort(
                    key=lambda r: (
                        str(r.get("date") or r.get("trade_date") or ""),
                        str(r.get("symbol") or ""),
                    )
                )
                curated = json.dumps(normalized, ensure_ascii=True, sort_keys=True).encode()
                key = f"data-drop/curated/{dataset.id}/v{next_version}-{row.id}.json"
                stored = self.storage.put_bytes(
                    key=key, data=curated, content_type="application/json"
                )
                version = models.DatasetVersion(
                    dataset_id=dataset.id,
                    version=next_version,
                    raw_object_id=raw.id,
                    row_count=len(normalized),
                    content_hash=row.content_hash,
                    schema_json={
                        "mapping": row.mapping,
                        "suffix": uploaded.content_type,
                        "licence": licence,
                        "profile_id": profile.id,
                        "profile_version": profile.version,
                        "file_id": row.id,
                        "columns": columns,
                        "quality": JSON_OBJECT.validate_python(validation),
                        "curated_key": key,
                        "curated_hash": stored.content_hash,
                        "point_in_time": "UNVERIFIED",
                        "adjustment_state": "UNADJUSTED",
                        "source": profile.source,
                    },
                )
                self.session.add(version)
                self.session.flush()
                self.session.add(
                    models.DatasetLineage(
                        dataset_version_id=version.id,
                        source_type="EXTERNAL_FILE",
                        source_id=row.id,
                        transform=json.dumps(
                            {
                                "profile": profile.code,
                                "version": profile.version,
                                "mapping": row.mapping,
                                "defaults": row.metadata_json.get("defaults"),
                                "resolution": row.metadata_json.get("symbol_resolution"),
                            }
                        ),
                    )
                )
                for column in columns:
                    self.session.add(
                        models.DatasetColumn(
                            dataset_version_id=version.id,
                            name=column,
                            inferred_type="source",
                            mapped_role=next(
                                (k for k, v in row.mapping.items() if v == column), None
                            ),
                        )
                    )
                instruments = {
                    i.symbol: i for i in self.session.scalars(select(models.Instrument)).all()
                }
                for index, record in enumerate(normalized):
                    if profile.dataset_type in {"ohlcv", "snapshot"}:
                        symbol = record["symbol"]
                        if not isinstance(symbol, str):
                            raise ValueError("Normalized security symbol must be text")
                        item = instruments[symbol]
                        observed_date = record["date"]
                        if not isinstance(observed_date, str):
                            raise ValueError("Normalized observation date must be text")
                        at = datetime.combine(
                            datetime.fromisoformat(observed_date).date(), time(20), UTC
                        )
                        self.session.add(
                            models.MarketObservation(
                                instrument_id=item.id,
                                timestamp=at,
                                price=decimal(record["close"]),
                                currency=item.currency,
                                source=profile.source,
                                source_category="FILE",
                                data_state="FILE IMPORT",
                                dataset_version_id=version.id,
                                source_file_id=row.id,
                                adjustment_state="UNADJUSTED",
                                fields={**record, "filename": row.filename, "licence": licence},
                            )
                        )
                    elif profile.dataset_type == "fx":
                        observed_date = record["date"]
                        if not isinstance(observed_date, str):
                            raise ValueError("Normalized observation date must be text")
                        at = datetime.combine(
                            datetime.fromisoformat(observed_date).date(), time(0), UTC
                        )
                        self.session.add(
                            models.FxObservation(
                                base_currency=record["base_currency"],
                                quote_currency=record["quote_currency"],
                                timestamp=at,
                                rate=decimal(record["rate"]),
                                source=profile.source,
                                source_category="FILE",
                                data_state="FILE IMPORT",
                                source_file_id=row.id,
                            )
                        )
                    elif profile.dataset_type == "transactions":
                        payload = {
                            **record,
                            "external_reference": record.get("external_reference")
                            or f"{row.content_hash}:{index}",
                        }
                        PortfolioLedgerService(self.session).add(
                            payload,
                            portfolio,
                            source=profile.source,
                            source_file_id=row.id,
                            actor=actor,
                        )
                row.dataset_version_id = version.id
                if profile.dataset_type in {"ohlcv", "snapshot", "fx"}:
                    from .portfolio_seed import profile_for

                    main_profile = profile_for(self.session, portfolio)
                    if main_profile and main_profile.configuration.get("price_mode") == "DEMO_ONLY":
                        main_profile.configuration = {
                            **main_profile.configuration,
                            "price_mode": "AUTO",
                        }
                        audit(
                            self.session,
                            "PORTFOLIO_APPROVED_EXTERNAL_PRICES",
                            "portfolio",
                            main_profile.portfolio_id,
                            {"from": "DEMO_ONLY", "to": "AUTO", "file_id": row.id},
                            actor,
                        )
                row.metadata_json = {
                    **row.metadata_json,
                    "licence": licence,
                    "dataset_id": dataset.id,
                    "curated_key": key,
                }
                uploaded.upload_state = "IMPORTED"
                audit(
                    self.session,
                    "EXTERNAL_FILE_IMPORTED",
                    "external_file",
                    row.id,
                    {
                        "dataset_id": dataset.id,
                        "version_id": version.id,
                        "profile_version": profile.version,
                        "licence": licence,
                        "portfolio": portfolio,
                    },
                    actor,
                )
                self.session.flush()
            transition(row, "IMPORTED")
            self.session.commit()
        except (ValueError, IntegrityError, OSError) as exc:
            transition(row, "IMPORT_FAILED", f"Atomic import rolled back: {type(exc).__name__}")
            row.validation = {
                **row.validation,
                "import_error": str(exc)[:300]
                if isinstance(exc, ValueError)
                else "Import storage or uniqueness conflict",
            }
            self.session.commit()
        return file_payload(row)
