"""Pinned FX validation must precede data access and retain the original evidence."""

from copy import deepcopy
from datetime import date, timedelta

import pytest
from app.quant_data import DatasetProvenance
from app.terminal_worker import backtest_result
from pydantic import JsonValue
from sqlalchemy.orm import Session


@pytest.fixture
def pinned_parameters() -> dict[str, JsonValue]:
    return {
        "symbol": "AAA",
        "base_currency": "SGD",
        "fast": 2,
        "slow": 5,
        "fee_bps": 0,
        "slippage_bps": 0,
        "description": "Unmodified fixture metadata",
        "_datasets": {
            "AAA": {
                "dataset_version_id": "fixture-v1",
                "dataset_id": "fixture-dataset",
                "version": 1,
                "content_hash": "a" * 64,
                "schema": {"currency": "USD"},
                "source": "FIXTURE",
                "quality": "TEST",
                "rows": 65,
                "vendor_evidence": "Must remain in the original response",
            }
        },
        "_fx": {
            "AAA": {
                (date(2024, 1, 1) + timedelta(days=day)).isoformat(): {
                    "rate": "1.300000000000",
                    "provenance": {"source": "FIXTURE", "data_state": "TEST"},
                }
                for day in range(65)
            }
        },
        "_sectors": {"AAA": "TEST"},
    }


@pytest.mark.parametrize(
    "rate", [0, -1, "NaN", "Infinity", "-Infinity", "invalid", None, True, "1e9999", "1e-9999"]
)
def test_invalid_pinned_fx_is_rejected_before_reading_any_dataset(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    pinned_parameters: dict[str, JsonValue],
    rate: JsonValue,
) -> None:
    pinned_parameters["_fx"] = {
        "AAA": {"2024-01-01": {"rate": rate, "provenance": {"source": "FIXTURE"}}}
    }

    def unexpected(_session: Session, _version: str) -> None:
        pytest.fail("Invalid FX must be rejected before dataset access or simulation")

    monkeypatch.setattr("app.quant_data.dataset_rows", unexpected)
    with pytest.raises(ValueError):
        backtest_result(ledger_session, pinned_parameters)


@pytest.mark.parametrize("fx", [{}, {"WRONG": {}}])
def test_missing_or_mismatched_fx_security_is_rejected_before_data_access(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    pinned_parameters: dict[str, JsonValue],
    fx: dict[str, JsonValue],
) -> None:
    pinned_parameters["_fx"] = fx

    def unexpected(_session: Session, _version: str) -> None:
        pytest.fail("Mismatched FX must not load a dataset")

    monkeypatch.setattr("app.quant_data.dataset_rows", unexpected)
    with pytest.raises(ValueError, match="own FX fixing"):
        backtest_result(ledger_session, pinned_parameters)


def test_valid_pins_preserve_raw_decimal_strings_vendor_evidence_and_zero_cost(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    pinned_parameters: dict[str, JsonValue],
) -> None:
    def fixture_dataset(
        _session: Session, version: str
    ) -> tuple[list[dict[str, JsonValue]], DatasetProvenance]:
        assert version == "fixture-v1"
        rows: list[dict[str, JsonValue]] = [
            {
                "date": (date(2024, 1, 1) + timedelta(days=day)).isoformat(),
                "symbol": "AAA",
                "open": 100 + day,
                "high": 102 + day,
                "low": 99 + day,
                "close": 101 + day,
            }
            for day in range(65)
        ]
        return rows, {
            "dataset_version_id": version,
            "dataset_id": "fixture-dataset",
            "version": 1,
            "content_hash": "a" * 64,
            "schema": {"currency": "USD"},
            "source": "FIXTURE",
            "quality": "TEST",
            "rows": len(rows),
        }

    monkeypatch.setattr("app.quant_data.dataset_rows", fixture_dataset)
    before = deepcopy(pinned_parameters)
    result = backtest_result(ledger_session, pinned_parameters)
    assert pinned_parameters == before
    assert result["inputs"] == before["_datasets"] and result["fx"] == before["_fx"]
    assert result["currency"] == "SGD" and result["quality"] == "TEST"
    assert result["source"] == "FIXTURE"
    assert result["parameters"] == {
        key: value for key, value in before.items() if not key.startswith("_")
    }
    metrics = result["metrics"]
    assert isinstance(metrics, dict)
    assert metrics["cost_drag"] == 0 and metrics["commission"] == 0
    assert metrics["cagr"] is None
    assert result["equity_curve"] == result["gross_equity_curve"]
