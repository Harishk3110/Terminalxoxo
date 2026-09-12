"""Saved research cannot borrow mutable inputs or accept forged receipt metadata."""

import hashlib
import json
from copy import deepcopy
from decimal import Decimal
from typing import Literal

import pytest
from app import models
from app.equity_api import save_analysis
from pydantic import JsonValue
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@pytest.mark.parametrize("boundary", ["parameters", "result", "response"])
def test_saved_analysis_owns_its_nested_evidence(
    ledger_session: Session,
    boundary: Literal["parameters", "result", "response"],
) -> None:
    settings: dict[str, JsonValue] = {"fee": 0, "missing": None, "label": "Original"}
    observation: dict[str, JsonValue] = {"amount": "1.200000000000", "label": "Original"}
    parameters: dict[str, JsonValue] = {"settings": settings}
    result: dict[str, JsonValue] = {"value": 0, "missing": None, "observation": observation}
    before_parameters, before_result = deepcopy(parameters), deepcopy(result)
    response = save_analysis(ledger_session, "wacc", "Test evidence", parameters, result, None)
    identifier = response["id"]
    assert isinstance(identifier, str)
    saved = ledger_session.get(models.AnalysisRun, identifier)
    assert saved is not None and saved.result is not None
    digest = hashlib.sha256(
        json.dumps(
            {"parameters": before_parameters, "result": before_result},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()
    assert response["input_hash"] == digest
    assert response["value"] == 0 and response["missing"] is None
    if boundary == "parameters":
        settings["label"] = "Changed by caller"
    elif boundary == "result":
        observation["label"] = "Changed by caller"
    else:
        returned = response["observation"]
        assert isinstance(returned, dict)
        returned["label"] = "Changed by recipient"
    assert saved.parameters == before_parameters
    assert saved.result == {
        **before_result,
        "input_hash": digest,
        "calculated_at": response["calculated_at"],
    }


@pytest.mark.parametrize("field", ["id", "input_hash", "calculated_at"])
def test_reserved_receipt_metadata_is_rejected_before_persistence(
    ledger_session: Session,
    field: str,
) -> None:
    with pytest.raises(ValueError, match="reserved"):
        save_analysis(ledger_session, "wacc", "Invalid receipt", {}, {field: "forged"}, None)
    assert ledger_session.scalar(select(func.count(models.AnalysisRun.id))) == 0
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == 0


@pytest.mark.parametrize("field", ["parameters", "result"])
@pytest.mark.parametrize(
    "value", [float("nan"), float("inf"), float("-inf"), {1, 2}, Decimal("1.23")]
)
def test_invalid_json_never_persists_an_analysis_or_audit(
    ledger_session: Session,
    field: Literal["parameters", "result"],
    value: object,
) -> None:
    parameters: dict[str, object] = {"field": value} if field == "parameters" else {}
    result: dict[str, object] = {"field": value} if field == "result" else {}
    with pytest.raises((ValueError, TypeError)):
        save_analysis(ledger_session, "wacc", "Invalid input", parameters, result, None)
    assert ledger_session.scalar(select(func.count(models.AnalysisRun.id))) == 0
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == 0
