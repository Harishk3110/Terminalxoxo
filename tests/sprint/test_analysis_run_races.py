"""Deterministic interleavings across independent database sessions."""

from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from datetime import UTC, datetime
from pathlib import Path

import pytest
from app import models, portfolio_api, terminal_api, terminal_worker
from app.analysis_lifecycle import transition_run
from fastapi import HTTPException
from pydantic import JsonValue
from sqlalchemy import create_engine, delete, event, select, update
from sqlalchemy.engine import Connection, Engine, ExecutionContext
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request


@pytest.fixture
def run_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[sessionmaker[Session]]:
    engine = create_engine(f"sqlite:///{(tmp_path / 'analysis-races.db').as_posix()}")
    models.Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(terminal_worker, "SessionLocal", factory)
    monkeypatch.setattr("app.worker_health.heartbeat", lambda _: nullcontext())
    monkeypatch.setattr(portfolio_api, "identity", lambda *_: "race-actor")
    with factory() as session:
        session.add(
            models.User(
                id="race-actor",
                email="analysis-race@example.test",
                password_hash="fixture-only",
                role="ADMIN",
            )
        )
        session.add(
            models.AnalysisRun(
                id="race-run",
                name="Isolated analytical run",
                kind="stress",
                parameters={},
                status="QUEUED",
                history=[{"state": "QUEUED", "at": "2026-01-01T00:00:00Z", "message": "Submitted"}],
            )
        )
        session.commit()
    yield factory
    engine.dispose()


def target_update(statement: str, parameters: object, state: str) -> bool:
    return (
        statement.startswith("UPDATE analysis_runs SET")
        and isinstance(parameters, tuple)
        and state in parameters
    )


@pytest.mark.parametrize("outcome", ["SUCCEEDED", "FAILED"])
def test_worker_cannot_overwrite_a_committed_cancellation(
    run_sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch, outcome: str
) -> None:
    def calculate(_session: Session, _parameters: dict[str, JsonValue]) -> dict[str, JsonValue]:
        if outcome == "FAILED":
            raise ValueError("Deterministic calculation failure")
        return {"quality": "TEST", "metric": 0}

    monkeypatch.setattr(terminal_worker, "stress_result", calculate)
    with run_sessions() as session:
        engine = session.get_bind()
    assert isinstance(engine, Engine)
    interleaved = False

    def cancel_before_write(
        _connection: Connection,
        _cursor: object,
        statement: str,
        parameters: object,
        _context: ExecutionContext,
        _executemany: bool,
    ) -> None:
        nonlocal interleaved
        if interleaved or not target_update(statement, parameters, outcome):
            return
        interleaved = True
        with run_sessions() as cancelling:
            terminal_api.cancel_run("race-run", Request({"type": "http"}), cancelling)

    event.listen(engine, "before_cursor_execute", cancel_before_write)
    try:
        terminal_worker.execute_run("race-run")
    finally:
        event.remove(engine, "before_cursor_execute", cancel_before_write)
    assert interleaved, "The competing cancellation must actually commit before the worker write"
    with run_sessions() as session:
        run = session.get(models.AnalysisRun, "race-run")
        assert run is not None
        assert run.status == "CANCELLED"
        assert run.result is None and run.error is None
        assert [entry["state"] for entry in run.history] == ["QUEUED", "RUNNING", "CANCELLED"]
        assert run.finished_at is not None
        assert session.scalar(select(models.AuditLog.action)) == "ANALYSIS_RUN_CANCELLED"


def test_cancellation_cannot_overwrite_a_committed_result(
    run_sessions: sessionmaker[Session],
) -> None:
    with run_sessions() as session:
        session.execute(update(models.AnalysisRun).values(status="RUNNING"))
        session.commit()
        engine = session.get_bind()
    assert isinstance(engine, Engine)
    interleaved = False

    def finish_before_cancel(
        _connection: Connection,
        _cursor: object,
        statement: str,
        parameters: object,
        _context: ExecutionContext,
        _executemany: bool,
    ) -> None:
        nonlocal interleaved
        if interleaved or not target_update(statement, parameters, "CANCELLED"):
            return
        interleaved = True
        with run_sessions() as completing:
            completing.execute(
                update(models.AnalysisRun)
                .where(
                    models.AnalysisRun.id == "race-run",
                )
                .values(status="SUCCEEDED", result={"metric": 0}, finished_at=datetime.now(UTC))
            )
            completing.commit()

    event.listen(engine, "before_cursor_execute", finish_before_cancel)
    try:
        with run_sessions() as cancelling:
            with pytest.raises(HTTPException) as rejected:
                terminal_api.cancel_run("race-run", Request({"type": "http"}), cancelling)
            assert rejected.value.status_code == 409
    finally:
        event.remove(engine, "before_cursor_execute", finish_before_cancel)
    assert interleaved
    with run_sessions() as session:
        run = session.get(models.AnalysisRun, "race-run")
        assert run is not None and run.status == "SUCCEEDED"
        assert run.result == {"metric": 0}
        assert session.scalar(select(models.AuditLog.id)) is None


def test_worker_failure_tolerates_a_removed_run(
    run_sessions: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def removed(session: Session, _parameters: dict[str, JsonValue]) -> dict[str, JsonValue]:
        session.execute(delete(models.AnalysisRun).where(models.AnalysisRun.id == "race-run"))
        session.commit()
        raise ValueError("Run was removed during calculation")

    monkeypatch.setattr(terminal_worker, "stress_result", removed)
    terminal_worker.execute_run("race-run")
    with run_sessions() as session:
        assert session.get(models.AnalysisRun, "race-run") is None


def test_claim_history_is_persisted_before_cancellation_can_arrive(
    run_sessions: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    @contextmanager
    def cancel_after_claim(_run_id: str) -> Iterator[None]:
        with run_sessions() as cancelling:
            terminal_api.cancel_run("race-run", Request({"type": "http"}), cancelling)
        yield

    def unexpected(_session: Session, _parameters: dict[str, JsonValue]) -> dict[str, JsonValue]:
        pytest.fail("A cancelled claimed run must not start a calculation")

    monkeypatch.setattr("app.worker_health.heartbeat", cancel_after_claim)
    monkeypatch.setattr(terminal_worker, "stress_result", unexpected)
    terminal_worker.execute_run("race-run")
    with run_sessions() as session:
        run = session.get(models.AnalysisRun, "race-run")
        assert run is not None
        assert run.status == "CANCELLED"
        assert [entry["state"] for entry in run.history] == ["QUEUED", "RUNNING", "CANCELLED"]
        assert run.started_at is not None and run.finished_at is not None
        assert run.result is None


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), -float("inf"), object()])
def test_invalid_result_is_failed_without_leaving_a_running_job(
    run_sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    def invalid_result(_session: Session, _parameters: dict[str, JsonValue]) -> dict[str, object]:
        return {"nested": [{"metric": invalid}]}

    monkeypatch.setattr(terminal_worker, "stress_result", invalid_result)
    terminal_worker.execute_run("race-run")
    with run_sessions() as session:
        run = session.get(models.AnalysisRun, "race-run")
        assert run is not None and run.status == "FAILED"
        assert run.result is None and run.error
        assert run.started_at is not None and run.finished_at is not None
        assert [entry["state"] for entry in run.history] == ["QUEUED", "RUNNING", "FAILED"]


def test_cancellation_cannot_erase_a_concurrent_claim_history(
    run_sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(terminal_worker, "_execute_run", lambda _: None)
    with run_sessions() as session:
        engine = session.get_bind()
    assert isinstance(engine, Engine)
    interleaved = False

    def claim_before_cancel(
        _connection: Connection,
        _cursor: object,
        statement: str,
        parameters: object,
        _context: ExecutionContext,
        _executemany: bool,
    ) -> None:
        nonlocal interleaved
        if interleaved or not target_update(statement, parameters, "CANCELLED"):
            return
        interleaved = True
        terminal_worker.execute_run("race-run")

    event.listen(engine, "before_cursor_execute", claim_before_cancel)
    try:
        with run_sessions() as cancelling:
            with pytest.raises(HTTPException) as rejected:
                terminal_api.cancel_run("race-run", Request({"type": "http"}), cancelling)
            assert rejected.value.status_code == 409
    finally:
        event.remove(engine, "before_cursor_execute", claim_before_cancel)
    assert interleaved
    with run_sessions() as session:
        run = session.get(models.AnalysisRun, "race-run")
        assert run is not None and run.status == "RUNNING"
        assert [entry["state"] for entry in run.history] == ["QUEUED", "RUNNING"]
        assert run.started_at is not None and run.finished_at is None
        assert session.scalar(select(models.AuditLog.id)) is None


@pytest.mark.parametrize("invalid", [None, [], 1, "invalid result"])
def test_non_object_result_is_failed(
    run_sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch, invalid: object
) -> None:
    monkeypatch.setattr(terminal_worker, "stress_result", lambda *_: invalid)
    terminal_worker.execute_run("race-run")
    with run_sessions() as session:
        run = session.get(models.AnalysisRun, "race-run")
        assert run is not None and run.status == "FAILED"
        assert run.result is None and run.error == "Analytical result must be a JSON object"
        assert run.finished_at is not None
        assert [entry["state"] for entry in run.history] == ["QUEUED", "RUNNING", "FAILED"]


def test_successful_result_preserves_zero_missing_values_and_nested_evidence(
    run_sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    expected: dict[str, JsonValue] = {
        "metric": 0,
        "unavailable": None,
        "returns": [0.0, -0.25, 0.75],
        "evidence": {"source": "FIXTURE", "quality": "TEST", "verified": True},
    }
    monkeypatch.setattr(terminal_worker, "stress_result", lambda *_: expected)
    terminal_worker.execute_run("race-run")
    with run_sessions() as session:
        run = session.get(models.AnalysisRun, "race-run")
        assert run is not None and run.status == "SUCCEEDED"
        assert run.result == expected and run.error is None
        assert run.started_at is not None and run.finished_at is not None
        assert [entry["state"] for entry in run.history] == ["QUEUED", "RUNNING", "SUCCEEDED"]
        assert run.history[1]["message"] == "Validated template executing in isolated process"
        assert run.history[2]["message"] == "Result persisted"


@pytest.mark.parametrize("status", ["SUCCEEDED", "FAILED", "CANCELLED"])
def test_duplicate_delivery_cannot_execute_or_change_finished_runs(
    run_sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch, status: str
) -> None:
    stored: dict[str, JsonValue] = {"metric": 0, "source": "FIXTURE"}
    history: list[dict[str, JsonValue]] = [{"state": status, "message": "Prior result"}]
    with run_sessions() as session:
        session.execute(
            update(models.AnalysisRun).values(status=status, result=stored, history=history)
        )
        session.commit()

    def unexpected(_run_id: str) -> None:
        pytest.fail("Completed runs must not be claimed again")

    monkeypatch.setattr(terminal_worker, "_execute_run", unexpected)
    terminal_worker.execute_run("race-run")
    with run_sessions() as session:
        run = session.get(models.AnalysisRun, "race-run")
        assert run is not None and run.status == status
        assert run.result == stored and run.history == history


def test_result_persistence_failure_is_recorded_after_rollback(
    run_sessions: sessionmaker[Session], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(terminal_worker, "stress_result", lambda *_: {"metric": 0})
    with run_sessions() as session:
        engine = session.get_bind()
    assert isinstance(engine, Engine)
    intercepted = False

    def reject_result_write(
        _connection: Connection,
        _cursor: object,
        statement: str,
        parameters: object,
        _context: ExecutionContext,
        _executemany: bool,
    ) -> None:
        nonlocal intercepted
        if target_update(statement, parameters, "SUCCEEDED"):
            intercepted = True
            raise ValueError("Deterministic result persistence failure")

    event.listen(engine, "before_cursor_execute", reject_result_write)
    try:
        terminal_worker.execute_run("race-run")
    finally:
        event.remove(engine, "before_cursor_execute", reject_result_write)
    assert intercepted
    with run_sessions() as session:
        run = session.get(models.AnalysisRun, "race-run")
        assert run is not None and run.status == "FAILED"
        assert run.result is None and run.error == "Deterministic result persistence failure"
        assert run.finished_at is not None
        assert [entry["state"] for entry in run.history] == ["QUEUED", "RUNNING", "FAILED"]


@pytest.mark.parametrize("competing_state", ["QUEUED", "RUNNING", "SUCCEEDED", "CANCELLED"])
def test_launcher_failure_cannot_replace_worker_or_cancellation_state(
    run_sessions: sessionmaker[Session],
    monkeypatch: pytest.MonkeyPatch,
    competing_state: str,
) -> None:
    monkeypatch.setattr("app.monte_carlo.pin_monte_carlo", lambda *_: {})

    def failed_launch(run_id: str) -> None:
        with run_sessions() as competing:
            if competing_state in {"RUNNING", "SUCCEEDED"}:
                assert transition_run(competing, run_id, "RUNNING")
                competing.commit()
            if competing_state == "SUCCEEDED":
                assert transition_run(competing, run_id, "SUCCEEDED", result={"metric": 0})
                competing.commit()
            elif competing_state == "CANCELLED":
                terminal_api.cancel_run(run_id, Request({"type": "http"}), competing)
        raise OSError("Private launch exception details")

    monkeypatch.setattr(terminal_api, "launch_worker", failed_launch)
    with run_sessions() as session:
        response = terminal_api.start_run(
            terminal_api.RunRequest(kind="monte_carlo", name="Launch race", parameters={}),
            Request({"type": "http"}),
            session,
        )
        expected = "FAILED" if competing_state == "QUEUED" else competing_state
        assert response["status"] == expected
        identifier = response["id"]
        assert isinstance(identifier, str)
        run = session.get(models.AnalysisRun, identifier)
        assert run is not None and run.status == expected
        if competing_state == "QUEUED":
            assert run.error == "Worker launch failed: OSError"
            assert run.started_at is None and run.finished_at is not None
            assert [entry["state"] for entry in run.history] == ["QUEUED", "FAILED"]
        else:
            assert run.error is None
            assert run.history[-1]["state"] == competing_state
            assert run.result == ({"metric": 0} if competing_state == "SUCCEEDED" else None)
