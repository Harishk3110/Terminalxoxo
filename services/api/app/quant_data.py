"""Hash-verified dataset inputs shared by research engines."""

import hashlib
import json
from typing import TypedDict

from pydantic import BaseModel, Field, JsonValue, TypeAdapter
from sqlalchemy.orm import Session

from . import models
from .object_storage import ObjectStorage
from .services import infer_tabular


class DatasetSourceContract(BaseModel):
    curated_key: str | None = Field(default=None, min_length=1)
    curated_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    suffix: str = "csv"
    mapping: dict[str, str] = Field(default_factory=dict)


class DatasetProvenance(TypedDict):
    dataset_version_id: str
    dataset_id: str | None
    version: int
    content_hash: str
    schema: dict[str, JsonValue]
    source: str
    quality: str
    rows: int


JSON_ROWS = TypeAdapter(list[dict[str, JsonValue]])


def dataset_rows(
    session: Session, version_id: str
) -> tuple[list[dict[str, JsonValue]], DatasetProvenance]:
    version = session.get(models.DatasetVersion, version_id)
    if version is None:
        raise ValueError("A persisted dataset version is required")
    raw = session.get(models.RawObject, version.raw_object_id)
    dataset = session.get(models.Dataset, version.dataset_id) if version.dataset_id else None
    schema = version.schema_json or {}
    contract = DatasetSourceContract.model_validate(schema)
    if raw is None:
        raise ValueError("Dataset raw object is unavailable")
    storage = ObjectStorage()
    key = contract.curated_key or raw.object_key
    expected_hash = contract.curated_hash if contract.curated_key else raw.content_hash
    if expected_hash is None:
        raise ValueError("Curated dataset requires a content hash")
    try:
        content = storage.get_bytes(key)
    except OSError as exc:
        raise ValueError("Dataset object is unavailable") from exc
    if len(content) > 100_000_000 or hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError("Dataset size or integrity check failed")
    if contract.curated_key:
        parsed: object = json.loads(content)
    else:
        raw_rows, _ = infer_tabular(content, contract.suffix)
        parsed = [
            {**row, **{role: row.get(column) for role, column in contract.mapping.items()}}
            for row in raw_rows
        ]
    if (
        not isinstance(parsed, list)
        or len(parsed) > 250000
        or any(not isinstance(row, dict) for row in parsed)
    ):
        raise ValueError("Dataset requires at most 250,000 tabular rows")
    rows = JSON_ROWS.validate_python(parsed, strict=True)
    # JsonValue permits non-finite floats; curated research inputs must not.
    json.dumps(rows, allow_nan=False)
    return rows, {
        "dataset_version_id": version.id,
        "dataset_id": version.dataset_id,
        "version": version.version,
        "content_hash": expected_hash,
        "schema": schema,
        "source": dataset.source if dataset else raw.provider,
        "quality": dataset.quality if dataset else "USER PROVIDED",
        "rows": len(rows),
    }
