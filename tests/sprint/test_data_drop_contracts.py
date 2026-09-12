"""Persisted import contracts must fail before changing a validated file."""

from copy import deepcopy
from pathlib import Path

import pytest
from app import models
from app.data_drop import DataDropService, file_payload
from app.data_mapping import seed_profiles
from pydantic import JsonValue
from sqlalchemy import select
from sqlalchemy.orm import Session


@pytest.fixture
def prepared_drop(ledger_session: Session, tmp_path: Path) -> tuple[DataDropService, str, str]:
    service = DataDropService(ledger_session)
    service.storage.local_root = tmp_path
    service.storage._s3 = None
    seed_profiles(ledger_session)
    profile = ledger_session.scalar(
        select(models.MappingProfile).where(models.MappingProfile.code == "GENERIC_OHLCV")
    )
    assert profile is not None
    received = service.receive("prices.csv", b"symbol,date,close\nAAA,2026-01-09,123.45678901\n")
    identifier = received["id"]
    assert isinstance(identifier, str)
    assert received["state"] == "MAPPING_REQUIRED"
    return service, identifier, profile.id


def test_missing_raw_reference_is_an_explicit_validation_error(
    prepared_drop: tuple[DataDropService, str, str], ledger_session: Session
) -> None:
    service, identifier, _ = prepared_drop
    row = service.get(identifier)
    row.uploaded_file_id = None
    ledger_session.commit()
    with pytest.raises(ValueError, match="[Rr]aw"):
        service.raw_rows(row)
    assert row.state == "MAPPING_REQUIRED"


def test_missing_approved_profile_fails_before_import_transition(
    prepared_drop: tuple[DataDropService, str, str], ledger_session: Session
) -> None:
    service, identifier, profile = prepared_drop
    service.map_validate(identifier, profile)
    row = service.get(identifier)
    row.profile_id = None
    ledger_session.commit()
    before = deepcopy(row.history)
    with pytest.raises(ValueError, match="[Pp]rofile"):
        service.import_file(identifier, name="Fixture", licence="Private fixture", approve=True)
    assert row.state == "AWAITING_APPROVAL"
    assert row.history == before
    assert ledger_session.scalars(select(models.DatasetVersion)).all() == []


@pytest.mark.parametrize(
    "field,value",
    [("defaults", []), ("defaults", {"note": float("nan")}), ("symbol_resolution", {})],
)
def test_malformed_persisted_mapping_is_rejected_before_import(
    prepared_drop: tuple[DataDropService, str, str],
    ledger_session: Session,
    field: str,
    value: JsonValue,
) -> None:
    service, identifier, profile = prepared_drop
    service.map_validate(identifier, profile)
    row = service.get(identifier)
    row.metadata_json = {**row.metadata_json, field: value}
    ledger_session.commit()
    before = deepcopy(row.history)
    with pytest.raises(ValueError):
        service.import_file(identifier, name="Fixture", licence="Private fixture", approve=True)
    assert row.state == "AWAITING_APPROVAL"
    assert row.history == before
    assert ledger_session.scalars(select(models.DatasetVersion)).all() == []


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_mapping_defaults_are_rejected_before_mapping_transition(
    prepared_drop: tuple[DataDropService, str, str], value: float
) -> None:
    service, identifier, profile = prepared_drop
    row = service.get(identifier)
    before = deepcopy(row.history)
    with pytest.raises(ValueError):
        service.map_validate(identifier, profile, defaults={"note": value})
    assert row.state == "MAPPING_REQUIRED"
    assert row.history == before


def test_valid_explicit_zero_defaults_are_persisted_without_coercion(
    prepared_drop: tuple[DataDropService, str, str],
) -> None:
    service, identifier, profile = prepared_drop
    result = service.map_validate(identifier, profile, defaults={"volume": 0})
    assert result["state"] == "AWAITING_APPROVAL"
    assert result["metadata"]["defaults"] == {"volume": 0}
    preview = result["metadata"]["normalized_preview"]
    assert isinstance(preview, list)
    assert isinstance(preview[0], dict)
    assert preview[0]["volume"] == "0"


def test_file_response_does_not_expose_mutable_persisted_containers(
    prepared_drop: tuple[DataDropService, str, str],
) -> None:
    service, identifier, profile = prepared_drop
    service.map_validate(identifier, profile)
    row = service.get(identifier)
    before = deepcopy((row.metadata_json, row.mapping, row.validation, row.history))
    payload = file_payload(row)
    payload["metadata"]["columns"] = []
    payload["mapping"]["close"] = "incorrect"
    payload["validation"]["valid"] = False
    payload["history"][0]["state"] = "incorrect"
    assert (row.metadata_json, row.mapping, row.validation, row.history) == before
