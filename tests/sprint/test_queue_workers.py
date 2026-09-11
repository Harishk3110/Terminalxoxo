from contextlib import nullcontext

import pytest
from app import models, queue_worker, terminal_worker
from app.provider_data import NAMES
from sqlalchemy import select


def sessions(monkeypatch, ledger_session):
    monkeypatch.setattr(queue_worker, "SessionLocal", lambda: nullcontext(ledger_session))
    monkeypatch.setattr(terminal_worker, "SessionLocal", lambda: nullcontext(ledger_session))


def test_quant_claim_is_idempotent_and_cancelled_runs_are_not_executed(monkeypatch, ledger_session):
    sessions(monkeypatch, ledger_session)
    monkeypatch.setattr("app.worker_health.heartbeat", lambda key: nullcontext())
    run = models.AnalysisRun(
        kind="monte_carlo", name="One claim", parameters={}, status="QUEUED", history=[]
    )
    ledger_session.add(run)
    ledger_session.commit()
    calls = []
    monkeypatch.setattr(terminal_worker, "_execute_run", lambda key: calls.append(key))
    terminal_worker.execute_run(run.id)
    terminal_worker.execute_run(run.id)
    assert calls == [run.id]
    run.status = "CANCELLED"
    ledger_session.commit()
    terminal_worker.execute_run(run.id)
    assert calls == [run.id]


@pytest.mark.anyio
async def test_data_job_records_actual_probe_outcome(monkeypatch, ledger_session):
    sessions(monkeypatch, ledger_session)
    job = models.IngestionJob(
        job_type="provider_health_check",
        provider="SYSTEM",
        status="QUEUED",
        parameters={},
        correlation_id="test",
    )
    ledger_session.add(job)
    ledger_session.commit()
    row = models.ProviderConnection(
        provider_name="FRED",
        provider_type="macro",
        enabled=True,
        configured=True,
        connection_state="NOT_TESTED",
    )
    ledger_session.add(row)
    ledger_session.commit()
    monkeypatch.setattr(queue_worker, "NAMES", {"fred": NAMES["fred"]})
    monkeypatch.setattr(queue_worker, "connection", lambda session, key, settings: row)
    monkeypatch.setattr(queue_worker, "adapters", lambda settings: {"fred": object()})

    async def failed(*args):
        return {"connection_state": "AUTH_FAILED"}

    monkeypatch.setattr(queue_worker, "probe", failed)
    await queue_worker.execute_provider_job(job.id)
    ledger_session.refresh(job)
    assert job.status == "FAILED" and job.records_received == 1 and job.records_rejected == 1
    assert (
        ledger_session.scalar(select(models.IngestionJobRun)).log_payload["items"][0]["state"]
        == "AUTH_FAILED"
    )


@pytest.mark.anyio
async def test_unknown_data_job_fails_without_simulated_success(monkeypatch, ledger_session):
    sessions(monkeypatch, ledger_session)
    job = models.IngestionJob(
        job_type="unimplemented", status="QUEUED", parameters={}, correlation_id="test"
    )
    ledger_session.add(job)
    ledger_session.commit()
    await queue_worker.execute_provider_job(job.id)
    ledger_session.refresh(job)
    assert job.status == "FAILED" and job.records_accepted == 0


@pytest.mark.anyio
async def test_invalid_provider_job_actor_fails_before_network_call(monkeypatch, ledger_session):
    sessions(monkeypatch, ledger_session)
    job = models.IngestionJob(
        job_type="provider_health_check",
        status="QUEUED",
        parameters={"actor_id": {"unexpected": "object"}},
        correlation_id="test",
    )
    ledger_session.add(job)
    ledger_session.commit()

    def unexpected(*args):
        pytest.fail("Malformed jobs must not construct network adapters")

    monkeypatch.setattr(queue_worker, "adapters", unexpected)
    await queue_worker.execute_provider_job(job.id)
    ledger_session.refresh(job)
    assert job.status == "FAILED" and job.records_received == 0
    assert job.finished_at is not None and job.progress == 1


@pytest.mark.anyio
async def test_missing_or_finished_data_jobs_are_not_claimed(monkeypatch, ledger_session):
    sessions(monkeypatch, ledger_session)
    job = models.IngestionJob(
        job_type="provider_health_check", status="SUCCEEDED", parameters={}, correlation_id="test"
    )
    ledger_session.add(job)
    ledger_session.commit()
    await queue_worker.execute_provider_job("does-not-exist")
    await queue_worker.execute_provider_job(job.id)
    ledger_session.refresh(job)
    assert job.status == "SUCCEEDED" and job.started_at is None
