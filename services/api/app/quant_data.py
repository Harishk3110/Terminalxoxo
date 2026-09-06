"""Hash-verified dataset inputs shared by research engines."""

import hashlib
import json

from . import models
from .object_storage import ObjectStorage
from .services import infer_tabular


def dataset_rows(session, version_id: str) -> tuple[list[dict], dict]:
    version = session.get(models.DatasetVersion, version_id)
    if version is None:
        raise ValueError("A persisted dataset version is required")
    raw = session.get(models.RawObject, version.raw_object_id)
    dataset = session.get(models.Dataset, version.dataset_id) if version.dataset_id else None
    schema = version.schema_json or {}
    if raw is None:
        raise ValueError("Dataset raw object is unavailable")
    storage = ObjectStorage()
    key = schema.get("curated_key") or raw.object_key
    expected_hash = schema.get("curated_hash") if schema.get("curated_key") else raw.content_hash
    try:
        content = storage.get_bytes(key)
    except OSError as exc:
        raise ValueError("Dataset object is unavailable") from exc
    if len(content) > 100_000_000 or hashlib.sha256(content).hexdigest() != expected_hash:
        raise ValueError("Dataset size or integrity check failed")
    if schema.get("curated_key"):
        rows = json.loads(content)
    else:
        rows, _ = infer_tabular(content, schema.get("suffix", "csv"))
        mapping = schema.get("mapping", {})
        rows = [
            {**row, **{role: row.get(column) for role, column in mapping.items()}} for row in rows
        ]
    if (
        not isinstance(rows, list)
        or len(rows) > 250000
        or any(not isinstance(row, dict) for row in rows)
    ):
        raise ValueError("Dataset requires at most 250,000 tabular rows")
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
