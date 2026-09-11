import json
from pathlib import Path
from uuid import uuid4

import pytest
from app import models
from sqlalchemy.orm import Session


def test_legacy_health_consumes_structured_checks_not_response_object(
    ledger_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app import main

    observed = {"database": "ready", "redis": "failed: ConnectionError", "object_storage": "ready"}
    monkeypatch.setattr(main, "readiness_checks", lambda session: observed)
    monkeypatch.setattr(main, "providers", lambda session: {"items": []})
    result = main.system_health(ledger_session)
    assert result["checks"] == observed
    ready = main.ready(ledger_session)
    assert ready.status_code == 200
    assert json.loads(ready.body)["checks"] == observed


def test_metrics_zero_completed_or_removed_states(ledger_session: Session) -> None:
    from app import main

    job = models.IngestionJob(
        job_type="provider_health_check", status="QUEUED", correlation_id=str(uuid4())
    )
    ledger_session.add(job)
    ledger_session.commit()
    first = main.metrics(ledger_session).body.decode()
    assert 'knk_jobs_by_state{state="QUEUED"} 1.0' in first
    job.status = "SUCCEEDED"
    ledger_session.commit()
    second = main.metrics(ledger_session).body.decode()
    assert 'knk_jobs_by_state{state="QUEUED"} 0.0' in second
    assert 'knk_jobs_by_state{state="SUCCEEDED"} 1.0' in second


def test_backup_metrics_report_missing_and_failed_receipts(
    ledger_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from datetime import UTC, datetime

    from app import main

    monkeypatch.setattr(main.settings, "backup_dir", str(tmp_path))
    first = main.metrics(ledger_session).body.decode()
    assert 'knk_backup_state{state="NOT_VERIFIED"} 1.0' in first
    assert 'knk_backup_state{state="VERIFIED"} 0.0' in first
    (tmp_path / "latest-backup-attempt.json").write_text(
        json.dumps({"state": "FAILED", "attempted_at": datetime.now(UTC).isoformat()}),
        encoding="utf-8",
    )
    second = main.metrics(ledger_session).body.decode()
    assert 'knk_backup_state{state="FAILED"} 1.0' in second
    assert 'knk_backup_state{state="NOT_VERIFIED"} 0.0' in second
