import hashlib
from pathlib import Path

import pytest
from app import models
from app.config import get_settings
from app.object_storage import ObjectStorage
from app.quant_data import dataset_rows
from sqlalchemy.orm import Session


def dataset(session, monkeypatch, tmp_path, content, *, curated=True, schema_updates=None):
    monkeypatch.setattr(get_settings(), "object_storage_local_dir", str(tmp_path))
    key = "tests/research-input.json"
    digest = hashlib.sha256(content).hexdigest()
    ObjectStorage().put_bytes(key=key, data=content, content_type="application/json")
    raw = models.RawObject(
        provider="TEST",
        dataset="contract",
        object_key=key,
        content_hash=digest,
        content_type="application/json",
        size_bytes=len(content),
        correlation_id="test",
    )
    session.add(raw)
    session.flush()
    schema = {"curated_key": key, "curated_hash": digest} if curated else {"suffix": "json"}
    version = models.DatasetVersion(
        version=1,
        raw_object_id=raw.id,
        row_count=1,
        content_hash=digest,
        schema_json={**schema, **(schema_updates or {})},
    )
    session.add(version)
    session.flush()
    return version


@pytest.mark.parametrize("curated", [False, True])
@pytest.mark.parametrize("number", [b"NaN", b"Infinity", b"-Infinity", b"1e999"])
def test_hash_verified_inputs_still_reject_nonfinite_values(
    ledger_session, monkeypatch, tmp_path, curated, number
):
    version = dataset(
        ledger_session, monkeypatch, tmp_path, b'[{"close":' + number + b"}]", curated=curated
    )
    with pytest.raises(ValueError, match="JSON compliant"):
        dataset_rows(ledger_session, version.id)


@pytest.mark.parametrize(
    "updates",
    [
        {"curated_key": []},
        {"curated_key": ""},
        {"curated_hash": None},
        {"curated_hash": "invalid"},
        {"suffix": []},
        {"mapping": {"close": ["price"]}},
    ],
)
def test_invalid_dataset_metadata_is_rejected_before_object_read(
    ledger_session, monkeypatch, tmp_path, updates
):
    version = dataset(ledger_session, monkeypatch, tmp_path, b"[]", schema_updates=updates)

    def unexpected(*args):
        pytest.fail("Malformed dataset metadata must not reach storage")

    monkeypatch.setattr(ObjectStorage, "get_bytes", unexpected)
    with pytest.raises(ValueError):
        dataset_rows(ledger_session, version.id)


@pytest.mark.parametrize("content", [b"{}", b"[1]", b"[null]", b"[[]]"])
def test_curated_inputs_require_tabular_objects(ledger_session, monkeypatch, tmp_path, content):
    version = dataset(ledger_session, monkeypatch, tmp_path, content)
    with pytest.raises(ValueError, match="tabular rows"):
        dataset_rows(ledger_session, version.id)


def test_raw_mapping_preserves_zero_null_and_verified_provenance(
    ledger_session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    version = dataset(
        ledger_session,
        monkeypatch,
        tmp_path,
        b'[{"price":0,"volume":null,"nested":{"reviewed":false}}]',
        curated=False,
        schema_updates={"mapping": {"close": "price"}},
    )
    rows, provenance = dataset_rows(ledger_session, version.id)
    assert rows == [{"price": 0, "close": 0, "volume": None, "nested": {"reviewed": False}}]
    assert provenance["content_hash"] == version.content_hash
    assert provenance["dataset_id"] is None
    assert provenance["source"] == "TEST" and provenance["rows"] == 1
