from pathlib import Path

import pytest
from app import models
from app.database import get_session
from app.desks_api import CandidateConfiguration, router
from app.research_inputs import ResearchInput, pin_input
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_research_inputs import seed_bars


def test_candidate_boundaries_cannot_overlap() -> None:
    with pytest.raises(ValueError, match="chronological"):
        CandidateConfiguration(
            training_start="2024-01-01", training_end="2024-12-31", validation_start="2024-06-01"
        )


def test_candidate_review_preserves_prior_decisions_and_matches_versions(
    ledger_session: Session, session_token: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "object_storage_local_dir", str(tmp_path))
    seed_bars(ledger_session)
    version = pin_input(ledger_session, ResearchInput(source_mode="DEMO_RESEARCH"))[
        "dataset_version_id"
    ]
    run = models.AnalysisRun(
        kind="model",
        name="Test evidence",
        status="SUCCEEDED",
        parameters={"dataset_version_id": version},
        result={"calculation_version": "test-fixture"},
        history=[],
    )
    wrong = models.AnalysisRun(
        kind="model",
        name="Wrong evidence",
        status="SUCCEEDED",
        parameters={"dataset_version_id": "different"},
        result={},
        history=[],
    )
    ledger_session.add_all([run, wrong])
    ledger_session.commit()
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        response = client.post(
            "/api/v1/desks/candidates",
            json={
                "name": "Test candidate",
                "hypothesis": "A test hypothesis with sufficient detail",
                "dataset_version_id": version,
                "configuration": {
                    "universe": ["SPY"],
                    "features": ["momentum_21"],
                    "economic_rationale": "Test review workflow",
                },
            },
        )
        assert response.status_code == 200, response.text
        key = response.json()["id"]
        for state in ("RESEARCH", "REJECTED"):
            response = client.post(
                f"/api/v1/desks/candidates/{key}/review",
                json={
                    "state": state,
                    "note": "Recorded review rationale",
                    "analysis_run_ids": [run.id],
                },
            )
            assert response.status_code == 200, response.text
        candidate = ledger_session.get(models.ResearchCandidate, key)
        assert [row["state"] for row in candidate.review["history"]] == ["RESEARCH", "REJECTED"]
        assert candidate.configuration["features"] == ["momentum_21"]
        assert candidate.review["gates"]["paper_validation"] == "NOT CONNECTED"
        assert (
            client.post(
                f"/api/v1/desks/candidates/{key}/review",
                json={
                    "state": "RESEARCH",
                    "note": "Wrong version rejected",
                    "analysis_run_ids": [wrong.id],
                },
            ).status_code
            == 422
        )
        assert (
            client.post(
                f"/api/v1/desks/candidates/{key}/review",
                json={
                    "state": "APPROVED_FOR_FURTHER_REVIEW",
                    "note": "Unsupported promotion rejected",
                },
            ).status_code
            == 422
        )
