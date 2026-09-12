"""Malformed queued model requests cannot read datasets or write artifacts."""

import hashlib
from copy import deepcopy
from typing import NoReturn

import pandas as pd
import pytest
from app.model_lab import ModelSettings
from app.model_runs import model_result
from app.object_storage import StoredObject
from app.quant_data import DatasetProvenance
from pydantic import JsonValue
from sqlalchemy.orm import Session
from test_model_lab import bars


@pytest.mark.parametrize(
    "changes",
    [
        {"dataset_version_id": None},
        {"dataset_version_id": ""},
        {"dataset_version_id": 1},
        {"symbol": None},
        {"symbol": ""},
        {"symbol": 1},
        {"settings": None},
        {"settings": {"model": "UNAPPROVED"}},
        {"settings": {"regularisation": "NaN"}},
        {"start": []},
        {"end": True},
    ],
)
def test_invalid_model_request_rejects_before_dataset_access(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, JsonValue],
) -> None:
    def unexpected(_session: Session, _version: str) -> None:
        pytest.fail("Malformed model request must not read a dataset")

    monkeypatch.setattr("app.model_runs.dataset_rows", unexpected)
    with pytest.raises(ValueError):
        model_result(
            ledger_session,
            {"dataset_version_id": "fixture-v1", "symbol": "AAA", **changes},
            "invalid-request",
        )


@pytest.mark.parametrize("currency", [0, True, [], {}])
def test_invalid_currency_evidence_rejects_before_training(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    currency: JsonValue,
) -> None:
    def fixture_dataset(
        _session: Session,
        _version: str,
    ) -> tuple[list[dict[str, JsonValue]], DatasetProvenance]:
        return [], {
            "dataset_version_id": "fixture-v1",
            "dataset_id": "fixture",
            "version": 1,
            "content_hash": "a" * 64,
            "schema": {"currency": currency},
            "source": "FIXTURE",
            "quality": "TEST",
            "rows": 0,
        }

    def fixture_frame(
        _rows: list[dict[str, JsonValue]],
        _symbol: str,
        _start: str | None,
        _end: str | None,
    ) -> pd.DataFrame:
        return pd.DataFrame()

    def unexpected(_frame: pd.DataFrame, _settings: ModelSettings) -> NoReturn:
        pytest.fail("Malformed currency evidence must not train or produce artifacts")

    monkeypatch.setattr("app.model_runs.dataset_rows", fixture_dataset)
    monkeypatch.setattr("app.model_runs.bars_frame", fixture_frame)
    monkeypatch.setattr("app.model_runs.model_research", unexpected)
    with pytest.raises(ValueError):
        model_result(
            ledger_session,
            {"dataset_version_id": "fixture-v1", "symbol": "AAA"},
            "invalid-currency",
        )


@pytest.mark.parametrize(
    ("schema", "expected_currency"),
    [({}, "DATASET NATIVE"), ({"currency": "USD"}, "USD"), ({"currency": None}, None)],
)
def test_model_result_preserves_native_currency_zero_cost_and_artifact_evidence(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    schema: dict[str, JsonValue],
    expected_currency: str | None,
) -> None:
    frame = bars()
    rows: list[dict[str, JsonValue]] = [
        {
            "symbol": "AAA",
            "date": day.isoformat(),
            **{key: float(frame[key].iloc[index]) for key in ("open", "high", "low", "close")},
        }
        for index, day in enumerate(pd.DatetimeIndex(frame.index))
    ]
    evidence: DatasetProvenance = {
        "dataset_version_id": "fixture-v1",
        "dataset_id": "fixture",
        "version": 1,
        "content_hash": "a" * 64,
        "schema": schema,
        "source": "FIXTURE",
        "quality": "TEST",
        "rows": len(rows),
    }
    original = deepcopy(evidence)

    def fixture_dataset(
        _session: Session,
        version: str,
    ) -> tuple[list[dict[str, JsonValue]], DatasetProvenance]:
        assert version == evidence["dataset_version_id"]
        return rows, evidence

    written: list[bytes] = []

    class FixtureStorage:
        def put_bytes(self, *, key: str, data: bytes, content_type: str) -> StoredObject:
            assert key == "research-models/native-currency/model.joblib"
            assert content_type == "application/octet-stream" and data
            written.append(data)
            return StoredObject(key, hashlib.sha256(data).hexdigest(), len(data))

    monkeypatch.setattr("app.model_runs.dataset_rows", fixture_dataset)
    monkeypatch.setattr("app.model_runs.ObjectStorage", FixtureStorage)
    result = model_result(
        ledger_session,
        {
            "dataset_version_id": "fixture-v1",
            "symbol": "AAA",
            "settings": {"model": "RIDGE", "fee_bps": 0, "slippage_bps": 0},
        },
        "native-currency",
    )
    assert result["inputs"] == evidence == original
    assert result["source"] == "FIXTURE" and result["quality"] == "TEST"
    assert result["as_of"] == pd.Timestamp(frame.index[-1]).isoformat()
    assert result["settings"]["fee_bps"] == result["settings"]["slippage_bps"] == 0
    assert [run["partition"] for run in result["cost_backtests"]] == ["VALIDATION", "TEST"]
    for run in result["cost_backtests"]:
        assert run["currency"] == expected_currency
        assert run["metrics"]["commission"] == 0
        assert run["equity_curve"]
    assert len(written) == 1
    assert result["artifact"]["content_hash"] == hashlib.sha256(written[0]).hexdigest()
    assert result["artifact"]["size_bytes"] == len(written[0])
