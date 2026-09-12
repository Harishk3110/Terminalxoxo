from io import BytesIO
from zipfile import ZipFile

import pytest
from app import models, report_jobs
from app.monte_carlo import monte_carlo_result
from app.report_contracts import ReportRequest
from app.report_sources import capture
from pydantic import JsonValue
from sqlalchemy.orm import Session
from test_report_jobs import ReportHarness
from test_report_jobs import reports as reports


def test_completed_monte_carlo_can_be_pinned_for_a_quant_deck(ledger_session: Session) -> None:
    parameters: dict[str, JsonValue] = {
        "settings": {"paths": 100, "horizon": 5, "seed": 3110},
        "_returns": [0.001, -0.002, 0.003] * 20,
        "_evidence": {
            "backtest_run_id": "source-backtest",
            "source": "Dated fictional returns",
            "quality": "DEMO DATA",
            "as_of": "2026-01-09",
        },
    }
    result = monte_carlo_result(parameters)
    run = models.AnalysisRun(
        kind="monte_carlo",
        name="Saved simulation",
        status="SUCCEEDED",
        parameters=parameters,
        result=result,
    )
    ledger_session.add(run)
    ledger_session.flush()
    snapshot = capture(
        ledger_session, ReportRequest(kind="quant", format="pptx", analysis_run_id=run.id)
    )
    assert snapshot.references["analysis_run_id"] == run.id
    assert snapshot.payload["metrics"] == result["metrics"]
    assert snapshot.payload["fan"] == result["fan"]
    assert snapshot.payload["inputs"] == result["inputs"]
    assert snapshot.data_as_of == "2026-01-09"
    assert snapshot.source == "Dated fictional returns"
    assert snapshot.quality == "DEMO DATA"


@pytest.mark.parametrize("result", [None, {}])
def test_completed_run_without_results_cannot_generate_a_report(
    ledger_session: Session,
    result: dict[str, JsonValue] | None,
) -> None:
    run = models.AnalysisRun(
        kind="backtest",
        name="Missing result",
        status="SUCCEEDED",
        parameters={},
        result=result,
    )
    ledger_session.add(run)
    ledger_session.flush()
    with pytest.raises(ValueError, match="completed matching"):
        capture(ledger_session, ReportRequest(kind="backtest", analysis_run_id=run.id))


@pytest.mark.parametrize("kind", ["backtest", "alpha", "factor", "model", "montecarlo"])
def test_existing_quant_source_kinds_keep_their_results(
    ledger_session: Session,
    kind: str,
) -> None:
    run = models.AnalysisRun(
        kind=kind,
        name="Existing saved research",
        status="SUCCEEDED",
        parameters={},
        result={"source": "TEST", "quality": "FILE IMPORT", "metrics": {"value": "0"}},
    )
    ledger_session.add(run)
    ledger_session.flush()
    snapshot = capture(
        ledger_session, ReportRequest(kind="quant", format="pptx", analysis_run_id=run.id)
    )
    assert snapshot.payload["metrics"] == {"value": "0"}
    assert snapshot.references["analysis_run_id"] == run.id
    assert snapshot.data_as_of is None


def test_templates_and_worker_share_quant_source_kinds(reports: ReportHarness) -> None:
    client, factory = reports
    response = client.get("/api/v1/report-jobs/templates")
    assert response.status_code == 200
    templates = {item["kind"]: item for item in response.json()["items"]}
    assert templates["quant"]["analysis_kinds"] == [
        "backtest",
        "alpha",
        "factor",
        "model",
        "monte_carlo",
        "montecarlo",
    ]
    assert templates["comps"]["analysis_kinds"] == ["comparables"]
    for kind in ("portfolio", "risk", "macro", "equity"):
        assert templates[kind]["analysis_kinds"] == []
    with factory() as session:
        run = models.AnalysisRun(
            kind="monte_carlo",
            name="Persisted simulation",
            status="SUCCEEDED",
            parameters={},
            result={"source": "TEST", "quality": "DEMO DATA", "metrics": {"median_return": 0}},
        )
        session.add(run)
        session.commit()
        run_id = run.id
    response = client.post(
        "/api/v1/report-jobs",
        json={"kind": "quant", "format": "pptx", "analysis_run_id": run_id},
    )
    assert response.status_code == 202
    identifier = response.json()["id"]
    assert report_jobs.execute(identifier)
    job = client.get(f"/api/v1/report-jobs/{identifier}").json()
    assert job["status"] == "SUCCEEDED"
    source = client.get(job["source_url"]).json()
    assert source["references"]["analysis_run_id"] == run_id
    assert source["payload"]["metrics"]["median_return"] == 0
    content = client.get(job["download_url"])
    assert content.status_code == 200
    with ZipFile(BytesIO(content.content)) as archive:
        assert "ppt/presentation.xml" in archive.namelist()


@pytest.mark.parametrize(
    "kind,status",
    [("monte_carlo", status) for status in ("QUEUED", "RUNNING", "FAILED", "CANCELLED")]
    + [("stress", "SUCCEEDED")],
)
def test_quant_report_rejects_unfinished_or_unrelated_runs(
    ledger_session: Session,
    kind: str,
    status: str,
) -> None:
    run = models.AnalysisRun(
        kind=kind,
        name="Ineligible source",
        status=status,
        parameters={},
        result={"metrics": {"value": 0}},
    )
    ledger_session.add(run)
    ledger_session.flush()
    with pytest.raises(ValueError, match="completed matching"):
        capture(ledger_session, ReportRequest(kind="quant", format="pptx", analysis_run_id=run.id))
