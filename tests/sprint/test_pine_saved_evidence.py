"""Saved template integrity is checked before reading a comparison upload."""

import asyncio
import io

import pytest
from app import models
from app.equity_api import save_analysis
from app.pine_api import compare
from app.pine_research import PineSettings, generate
from app.pine_results import SavedPineTemplate
from fastapi import Request, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session


class UnreadUpload(UploadFile):
    async def read(self, size: int = -1) -> bytes:
        pytest.fail("Invalid saved evidence reached the upload reader")


@pytest.mark.parametrize(
    "damage",
    [
        "null_result",
        "missing_hash",
        "null_hash",
        "short_hash",
        "non_string_hash",
        "wrong_hash",
        "missing_source",
        "changed_source",
        "invalid_parameters",
        "different_parameters",
        "missing_recorded_settings",
        "different_recorded_settings",
    ],
)
def test_invalid_saved_template_is_rejected_before_upload_read(
    ledger_session: Session, damage: str
) -> None:
    settings = PineSettings()
    generated = generate(settings)
    result: SavedPineTemplate = {
        **generated,
        "pine_source": generated["source"],
        "source": "KnK Pine template generator",
    }
    receipt = save_analysis(
        ledger_session, "pine", "Saved template", settings.model_dump(mode="json"), result, None
    )
    identifier = receipt["id"]
    assert isinstance(identifier, str)
    row = ledger_session.get(models.AnalysisRun, identifier)
    assert row is not None and row.result is not None
    if damage == "null_result":
        row.result = None
    elif damage == "invalid_parameters":
        row.parameters = {"fast": 51}
    elif damage == "different_parameters":
        row.parameters = {**row.parameters, "fast": 21}
    else:
        changed = dict(row.result)
        if damage == "missing_hash":
            del changed["source_hash"]
        elif damage == "null_hash":
            changed["source_hash"] = None
        elif damage == "short_hash":
            changed["source_hash"] = "abc"
        elif damage == "non_string_hash":
            changed["source_hash"] = ["not a hash"]
        elif damage == "wrong_hash":
            changed["source_hash"] = "0" * 64
        elif damage == "missing_source":
            del changed["pine_source"]
        elif damage == "changed_source":
            changed["pine_source"] = "//@version=6\n// changed"
        elif damage == "missing_recorded_settings":
            del changed["settings"]
        elif damage == "different_recorded_settings":
            changed["settings"] = {**settings.model_dump(mode="json"), "fast": 21}
        row.result = changed
    ledger_session.commit()
    audit_count = ledger_session.scalar(select(func.count(models.AuditLog.id)))
    upload = UnreadUpload(file=io.BytesIO(b"unread"), filename="chart.csv")
    request = Request({"type": "http", "method": "POST", "path": "/", "headers": []})
    with pytest.raises(ValueError):
        asyncio.run(compare(identifier, request, ledger_session, upload))
    assert ledger_session.scalar(select(func.count(models.AnalysisRun.id))) == 1
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == audit_count
