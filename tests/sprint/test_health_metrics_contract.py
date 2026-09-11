import json
from uuid import uuid4

from app import models


def test_legacy_health_consumes_structured_checks_not_response_object(ledger_session, monkeypatch):
    from app import main

    observed = {"database": "ready", "redis": "failed: ConnectionError", "object_storage": "ready"}
    monkeypatch.setattr(main, "readiness_checks", lambda session: observed)
    monkeypatch.setattr(main, "providers", lambda session: {"items": []})
    result = main.system_health(ledger_session)
    assert result["checks"] == observed
    ready = main.ready(ledger_session)
    assert ready.status_code == 200
    assert json.loads(ready.body)["checks"] == observed


def test_metrics_zero_completed_or_removed_states(ledger_session):
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
