"""Imported financial evidence must be valid before it reaches a valuation."""

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pytest
from app import curated_fundamentals, models
from app.equity_contracts import FinancialEvidence
from app.object_storage import ObjectStorage
from pydantic import JsonValue
from sqlalchemy.orm import Session


@dataclass
class ImportedStatements:
    session: Session
    storage: ObjectStorage
    sequence: int = 0

    def add(
        self, rows: object, overrides: dict[str, JsonValue] | None = None
    ) -> models.DatasetVersion:
        self.sequence += 1
        content = json.dumps(rows).encode()
        key = f"curated/fixture-{self.sequence}.json"
        digest = hashlib.sha256(content).hexdigest()
        self.storage.put_bytes(key=key, data=content, content_type="application/json")
        raw = models.RawObject(
            provider="FICTIONAL",
            dataset="statements",
            object_key=key,
            content_hash=digest,
            content_type="application/json",
            size_bytes=len(content),
            correlation_id=f"fixture-{self.sequence}",
        )
        dataset = models.Dataset(
            name=f"Fictional {self.sequence}",
            dataset_type="fundamentals_long",
            source="FICTIONAL",
            quality="FILE IMPORT",
        )
        self.session.add_all([raw, dataset])
        self.session.flush()
        version = models.DatasetVersion(
            dataset_id=dataset.id,
            version=1,
            raw_object_id=raw.id,
            row_count=len(rows) if isinstance(rows, list) else 1,
            content_hash=digest,
            schema_json={
                "curated_key": key,
                "curated_hash": digest,
                "file_id": f"fixture-{self.sequence}",
                "licence": "Fictional tests only",
                **(overrides or {}),
            },
        )
        self.session.add(version)
        self.session.flush()
        return version

    def read(self) -> FinancialEvidence | None:
        item = self.session.get(models.Instrument, "AAA")
        assert item is not None
        return curated_fundamentals.curated_statements(self.session, item)


@pytest.fixture
def imported(
    ledger_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> ImportedStatements:
    storage = ObjectStorage()
    storage.local_root, storage._s3 = tmp_path, None
    # The shared dataset reader must use the same isolated object store.
    monkeypatch.setattr("app.quant_data.ObjectStorage", lambda: storage)
    return ImportedStatements(ledger_session, storage)


def statement(**changes: JsonValue) -> dict[str, JsonValue]:
    return {
        "symbol": "AAA",
        "period": "2025",
        "frequency": "ANNUAL",
        "actual_estimate": "ACTUAL",
        "report_date": "2026-02-01",
        "unit": "SGD",
        "scale": "1000000",
        "metric": "revenue",
        "value": "100",
        **changes,
    }


@pytest.mark.parametrize(
    "overrides",
    [
        {"curated_key": 42},
        {"curated_hash": None},
        {"curated_hash": []},
        {"curated_hash": "invalid"},
    ],
)
def test_invalid_source_contract_rejects_before_storage_read(
    imported: ImportedStatements,
    monkeypatch: pytest.MonkeyPatch,
    overrides: dict[str, JsonValue],
) -> None:
    imported.add([statement()], overrides)
    reads: list[str] = []
    original = imported.storage.get_bytes

    def observed(key: str) -> bytes:
        reads.append(key)
        return original(key)

    monkeypatch.setattr(imported.storage, "get_bytes", observed)
    with pytest.raises(ValueError):
        imported.read()
    assert reads == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("period", None),
        ("period", True),
        ("frequency", []),
        ("actual_estimate", {}),
        ("report_date", None),
        ("unit", []),
        ("scale", "0"),
        ("scale", "-1"),
        ("scale", "NaN"),
        ("scale", "Infinity"),
        ("scale", True),
        ("value", "NaN"),
        ("value", "Infinity"),
        ("value", "1e999"),
        ("value", False),
        ("metrics", [1]),
        ("metrics", {"revenue": "NaN"}),
    ],
)
def test_malformed_statement_is_not_financial_evidence(
    imported: ImportedStatements,
    field: str,
    value: JsonValue,
) -> None:
    imported.add([statement(**{field: value})])
    with pytest.raises(ValueError):
        imported.read()


@pytest.mark.parametrize("payload", [{"rows": []}, [1], [None], ["AAA"]])
def test_curated_content_must_be_tabular(imported: ImportedStatements, payload: object) -> None:
    imported.add(payload)
    with pytest.raises(ValueError):
        imported.read()


@pytest.mark.parametrize("field", ["value", "extension"])
def test_nonfinite_json_is_not_curated_evidence(imported: ImportedStatements, field: str) -> None:
    imported.add([statement(**{field: float("nan")})])
    with pytest.raises(ValueError):
        imported.read()


@pytest.mark.parametrize(
    "value,scale",
    [
        ("0", "1000000"),
        ("-0.0", "1"),
        ("-123.45", "1000"),
        ("123456789.123456789", "0.01"),
        (10, 1000000),
        (0.1, "3"),
    ],
)
def test_valid_metric_conversion_keeps_existing_float_bits(
    imported: ImportedStatements,
    value: JsonValue,
    scale: JsonValue,
) -> None:
    imported.add([statement(value=value, scale=scale)])
    result = imported.read()
    assert isinstance(result, dict)
    actual = result["items"][0]["revenue"]
    assert isinstance(actual, float)
    expected = float(Decimal(str(value)) * Decimal(str(scale)) / 1_000_000)
    assert actual.hex() == expected.hex()


def test_partial_restatement_retains_prior_metric_values_and_sources(
    imported: ImportedStatements,
) -> None:
    first = imported.add([statement(metrics={"revenue": "100", "cash": "20"})])
    second = imported.add(
        [
            statement(value="110", report_date="2026-03-01"),
            statement(metric="debt", value="12", unit="SHARES", report_date="2026-03-01"),
        ]
    )
    result = imported.read()
    assert isinstance(result, dict)
    row = result["items"][0]
    assert row["revenue"] == 110 and row["cash"] == 20 and "debt" not in row
    sources = row["metric_sources"]
    assert isinstance(sources, dict)
    cash_source, revenue_source = sources["cash"], sources["revenue"]
    assert isinstance(cash_source, dict) and isinstance(revenue_source, dict)
    assert cash_source["version_id"] == first.id
    assert revenue_source["version_id"] == second.id
    assert row["report_date"] == "2026-03-01"
    assert result["quality"] == "FILE IMPORT"
    assert any("incompatible unit SHARES" in warning for warning in result["warnings"])


def test_legacy_optional_fields_and_empty_source_are_preserved(
    imported: ImportedStatements,
) -> None:
    imported.add([statement()], {"curated_key": None})
    assert imported.read() is None
    imported.add([statement(period=2025, metrics=None), {"symbol": "OTHER"}])
    result = imported.read()
    assert isinstance(result, dict)
    assert result["items"][0]["year"] == "2025"
    assert result["items"][0]["revenue"] == 100


def test_curated_hash_mismatch_is_not_accepted(imported: ImportedStatements) -> None:
    imported.add([statement()], {"curated_hash": "0" * 64})
    with pytest.raises(ValueError, match="integrity"):
        imported.read()
