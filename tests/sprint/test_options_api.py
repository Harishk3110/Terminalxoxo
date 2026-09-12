import io
from collections.abc import Iterator
from pathlib import Path

import pytest
from app import models
from app.config import get_settings
from app.data_drop import DataDropService
from app.data_mapping import seed_profiles
from app.database import get_session
from app.option_greeks import PricingInputs
from app.options_api import router
from app.options_data import load_chain
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import JsonValue
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@pytest.fixture
def options_client(
    ledger_session: Session, session_token: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    monkeypatch.setattr(get_settings(), "object_storage_local_dir", str(tmp_path))
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        yield client


def test_demo_is_explicit_and_saved_run_is_source_pinned(
    options_client: TestClient, ledger_session: Session
) -> None:
    response = options_client.post("/api/v1/options/calculate", json={"symbol": "AAA"})
    assert response.status_code == 422 and "DATA UNAVAILABLE" in response.text
    created = options_client.post("/api/v1/options/demo", json={"symbol": "AAA"})
    assert created.status_code == 201, created.text
    dataset = created.json()
    rows = options_client.get(f"/api/v1/options/datasets/{dataset['id']}").json()["items"]
    assert len(rows) == 30
    result = options_client.post(
        "/api/v1/options/calculate",
        json={
            "symbol": "AAA",
            "dataset_version_id": dataset["id"],
            "spot_override": 100,
            "legs": [{"option_symbol": rows[0]["option_symbol"], "quantity": 2}],
        },
    )
    assert result.status_code == 201, result.text
    saved = result.json()
    assert saved["quality"] == "DEMO DATA"
    assert saved["coverage"]["gex_included"] == 30
    assert saved["summary"]["net_gex"] < 0
    assert len(saved["input_hash"]) == 64 and saved["inputs"]["dataset_version_id"] == dataset["id"]
    assert saved["positions"]["state"] == "COMPLETE"
    assert len(saved["positions"]["payoff"]) == 101
    analysis = ledger_session.get(models.AnalysisRun, saved["id"])
    assert analysis is not None and analysis.kind == "options"
    assert saved["spot_provenance"] == {
        "source": "USER SPOT ASSUMPTION",
        "value": "100.0",
        "as_of": saved["as_of"],
        "data_state": "RESEARCH ASSUMPTION",
    }
    assert ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.action == "OPTIONS_CREATED")
    )


def test_auth_and_production_demo_guard(
    options_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "knk_env", "production")
    assert options_client.post("/api/v1/options/demo", json={"symbol": "AAA"}).status_code == 422
    options_client.cookies.clear()
    assert options_client.get("/api/v1/options/datasets").status_code == 403


def test_internal_book_has_actual_zero_option_positions_and_pinned_nav(
    options_client: TestClient,
) -> None:
    created = options_client.post("/api/v1/options/demo", json={"symbol": "AAA"}).json()
    response = options_client.post(
        "/api/v1/options/calculate",
        json={
            "symbol": "AAA",
            "dataset_version_id": created["id"],
            "spot_override": 100,
            "portfolio": "book",
        },
    )
    assert response.status_code == 201, response.text
    assert response.json()["valuation_run_id"]
    assert response.json()["positions"]["totals"]["gamma"] == 0
    assert response.json()["position_source"].startswith("INTERNAL LEDGER")


@pytest.mark.parametrize("suffix", ["csv", "xlsx"])
def test_options_file_validation_import_version_and_hash(
    options_client: TestClient, ledger_session: Session, suffix: str
) -> None:
    seed_profiles(ledger_session)
    ledger_session.commit()
    profile = ledger_session.scalar(
        select(models.MappingProfile).where(models.MappingProfile.code == "GENERIC_OPTIONS_CHAIN")
    )
    assert profile is not None
    columns = [
        "Underlying",
        "Option Symbol",
        "Expiration",
        "Strike",
        "Call Put",
        "Contract Multiplier",
        "Exercise Style",
        "Timestamp",
        "IV Unit",
        "IV",
        "Bid",
        "Ask",
        "Open Interest",
    ]
    values = [
        "AAA",
        "AAA-100-C",
        "2026-12-18",
        100,
        "CALL",
        100,
        "EUROPEAN",
        "2026-01-02T20:00:00Z",
        "PERCENT",
        25,
        3,
        4,
        1000,
    ]
    if suffix == "csv":
        content = (",".join(columns) + "\n" + ",".join(str(v) for v in values) + "\n").encode()
    else:
        from openpyxl import Workbook

        workbook = Workbook()
        sheet = workbook.active
        assert sheet is not None
        sheet.append(columns)
        sheet.append(values)
        stream = io.BytesIO()
        workbook.save(stream)
        content = stream.getvalue()
    drop = DataDropService(ledger_session)
    received = drop.receive(f"AAA_chain.{suffix}", content)
    validated = drop.map_validate(received["id"], profile.id)
    assert validated["validation"]["valid"], validated
    imported = drop.import_file(
        received["id"], name="Observed chain", licence="Internal test fixture", approve=True
    )
    assert imported["state"] == "IMPORTED", imported
    version_id = imported["dataset_version_id"]
    assert version_id is not None
    contracts, provenance = load_chain(ledger_session, version_id)
    assert contracts[0].volatility == 0.25 and contracts[0].currency == "SGD"
    assert provenance["quality"] == "FILE IMPORT"
    assert provenance["schema"]["file_id"] == received["id"]
    curated_key = provenance["schema"]["curated_key"]
    assert isinstance(curated_key, str)
    with pytest.raises(ValueError, match="integrity"):
        drop.storage.put_bytes(key=curated_key, data=b"[]", content_type="application/json")
        load_chain(ledger_session, version_id)


@pytest.mark.parametrize("price", [None, float("nan"), float("inf"), float("-inf"), -1.0])
def test_invalid_demo_price_is_rejected_before_storage(
    options_client: TestClient,
    ledger_session: Session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    price: float | None,
) -> None:
    def unavailable(_inputs: PricingInputs, advanced: bool = True) -> dict[str, float | None]:
        return {"theoretical_price": price}

    monkeypatch.setattr("app.options_api.greeks", unavailable)
    response = options_client.post("/api/v1/options/demo", json={"symbol": "AAA"})
    assert response.status_code == 422, response.text
    assert "finite non-negative theoretical price" in response.text
    assert not [path for path in tmp_path.rglob("*") if path.is_file()]
    for table in (models.Dataset, models.RawObject, models.DatasetVersion, models.DatasetLineage):
        assert ledger_session.scalar(select(func.count()).select_from(table)) == 0
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == 0


def test_real_zero_demo_price_remains_zero(
    options_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def zero(_inputs: PricingInputs, advanced: bool = True) -> dict[str, float | None]:
        return {"theoretical_price": 0.0}

    monkeypatch.setattr("app.options_api.greeks", zero)
    response = options_client.post("/api/v1/options/demo", json={"symbol": "AAA"})
    assert response.status_code == 201, response.text
    rows = options_client.get(f"/api/v1/options/datasets/{response.json()['id']}").json()["items"]
    assert len(rows) == 30
    assert all(row["last"] == 0.0 and row["bid"] == 0 and row["ask"] == 0.03 for row in rows)


@pytest.mark.parametrize("file_id", [12, False, 1.5, [], {}, ["file"], {"id": "file"}])
def test_dataset_discovery_rejects_malformed_file_reference(
    options_client: TestClient, ledger_session: Session, file_id: JsonValue
) -> None:
    response = options_client.post("/api/v1/options/demo", json={"symbol": "AAA"})
    assert response.status_code == 201, response.text
    version = ledger_session.get(models.DatasetVersion, response.json()["id"])
    assert version is not None and version.schema_json is not None
    version.schema_json = {**version.schema_json, "file_id": file_id}
    ledger_session.commit()
    discovered = options_client.get("/api/v1/options/datasets")
    assert discovered.status_code == 422, discovered.text


@pytest.mark.parametrize("file_id", [None, "file-reference"])
def test_dataset_discovery_preserves_optional_file_reference(
    options_client: TestClient, ledger_session: Session, file_id: str | None
) -> None:
    response = options_client.post("/api/v1/options/demo", json={"symbol": "AAA"})
    assert response.status_code == 201, response.text
    version = ledger_session.get(models.DatasetVersion, response.json()["id"])
    assert version is not None and version.schema_json is not None
    version.schema_json = {**version.schema_json, "file_id": file_id}
    ledger_session.commit()
    discovered = options_client.get("/api/v1/options/datasets")
    assert discovered.status_code == 200, discovered.text
    assert discovered.json()["items"][0]["file_id"] == file_id
