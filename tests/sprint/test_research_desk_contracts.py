"""Research summaries and candidate reviews consume validated persisted evidence."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest
from app import desks_api, models, terminal_analytics, terminal_api
from app.portfolio_valuation import PortfolioValuationService
from fastapi import HTTPException
from pydantic import JsonValue, TypeAdapter
from sqlalchemy.orm import Session
from starlette.requests import Request

JSON_OBJECT = TypeAdapter(dict[str, JsonValue])
JSON_ROWS = TypeAdapter(list[dict[str, JsonValue]])


@pytest.mark.parametrize("value", [None, True, False, {}, [], "NaN", "Infinity", float("inf")])
def test_metrics_reject_nonnumeric_or_nonfinite_values(value: object) -> None:
    with pytest.raises(ValueError):
        desks_api.finite_number(value)


@pytest.mark.parametrize("value", [0, "0", -1.25, "0.00000001"])
def test_metrics_preserve_zero_negative_and_small_values(value: str | float) -> None:
    assert desks_api.finite_number(value) == float(value)


@pytest.mark.parametrize(
    "parameters",
    [
        {"_datasets": None},
        {"_datasets": []},
        {"_datasets": {"SPY": "bad"}},
        {"dataset_version_id": 1},
        {"_datasets": {"SPY": {"dataset_version_id": []}}},
    ],
)
def test_lineage_rejects_wrong_shapes(parameters: dict[str, JsonValue]) -> None:
    with pytest.raises(ValueError):
        desks_api.dataset_versions(parameters)


def test_lineage_combines_exact_versions_without_mutating_input() -> None:
    parameters: dict[str, JsonValue] = {
        "dataset_version_id": "direct-v1",
        "_datasets": {
            "SPY": {"dataset_version_id": "spy-v2"},
            "QQQ": {"dataset_version_id": "qqq-v3"},
        },
    }
    before = deepcopy(parameters)
    assert desks_api.dataset_versions(parameters) == {"direct-v1", "spy-v2", "qqq-v3"}
    assert desks_api.dataset_versions({}) == set()
    assert parameters == before


def analysis(
    session: Session,
    kind: str,
    result: dict[str, JsonValue],
    parameters: dict[str, JsonValue] | None = None,
) -> models.AnalysisRun:
    row = models.AnalysisRun(
        kind=kind,
        name="Contract fixture",
        status="SUCCEEDED",
        parameters=parameters or {},
        result=result,
        history=[],
    )
    session.add(row)
    session.flush()
    return row


def test_quant_summary_uses_only_test_partition_and_preserves_negative_sharpe(
    ledger_session: Session,
) -> None:
    analysis(
        ledger_session,
        "model",
        {
            "cost_backtests": [
                {"partition": "VALIDATION", "metrics": {"sharpe": 99}},
                {"partition": "TEST", "metrics": {"sharpe": -0.75}},
                {"partition": "TEST", "metrics": {"sharpe": None}},
            ]
        },
    )
    result = desks_api.quant(ledger_session)
    summary = JSON_OBJECT.validate_python(result["summary"], strict=True)
    assert summary["best_oos_sharpe"] == -0.75
    assert summary["paper_strategies"] == 0
    assert result["paper_state"] == "NO VERIFIED PAPER PERFORMANCE"


def test_run_payload_preserves_history_and_filters_only_private_parameters(
    ledger_session: Session,
) -> None:
    run = analysis(
        ledger_session,
        "model",
        {"sharpe": -0.75, "missing": None, "zero": 0},
        {"dataset_version_id": "v1", "_datasets": {"SPY": "private"}},
    )
    run.history = [{"status": "QUEUED"}, {"status": "SUCCEEDED", "duration": 0}]
    expected_history = deepcopy(run.history)
    result = terminal_api.run_payload(run)
    assert result["parameters"] == {"dataset_version_id": "v1"}
    assert result["result"] == run.result
    assert result["history"] == expected_history
    assert run.history == expected_history
    assert result["started_at"] is None
    assert result["finished_at"] is None
    assert JSON_OBJECT.validate_python(result, strict=True) == result


@pytest.mark.parametrize("zero", [None, 0])
def test_absent_and_zero_oos_results_remain_distinct(
    ledger_session: Session, zero: int | None
) -> None:
    analysis(
        ledger_session,
        "model",
        {
            "cost_backtests": [
                {"partition": "TEST", "metrics": {"sharpe": zero}},
            ]
        },
    )
    result = desks_api.quant(ledger_session)
    assert JSON_OBJECT.validate_python(result["summary"], strict=True)["best_oos_sharpe"] == zero


def candidate(session: Session) -> models.ResearchCandidate:
    raw = models.RawObject(
        provider="TEST",
        dataset="review-contract",
        object_key="test/review",
        content_hash="a" * 64,
        content_type="application/json",
        size_bytes=2,
        correlation_id="test",
    )
    session.add(raw)
    session.flush()
    version = models.DatasetVersion(
        raw_object_id=raw.id, version=1, row_count=0, content_hash="a" * 64, schema_json={}
    )
    session.add(version)
    session.flush()
    row = models.ResearchCandidate(
        name="Contract candidate",
        hypothesis="Test recorded evidence",
        dataset_version_id=version.id,
        state="RESEARCH",
        configuration={},
        review={
            "history": [{"state": "IDEA"}],
            "evidence": [],
            "gates": {"paper_validation": "NOT CONNECTED"},
        },
    )
    session.add(row)
    session.flush()
    return row


def test_review_accepts_completed_parent_exact_version_and_keeps_history(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = candidate(ledger_session)
    parent = analysis(
        ledger_session,
        "backtest",
        {},
        {"_datasets": {"SPY": {"dataset_version_id": row.dataset_version_id}}},
    )
    evidence = analysis(
        ledger_session,
        "alpha",
        {"calculation_version": "alpha-contract"},
        {"backtest_run_id": parent.id},
    )
    monkeypatch.setattr(desks_api, "identity", lambda *_: None)
    result = desks_api.review_candidate(
        row.id,
        desks_api.CandidateReview(
            note="Verified exact recorded dataset", state="REJECTED", analysis_run_ids=[evidence.id]
        ),
        Request({"type": "http", "headers": []}),
        ledger_session,
    )
    assert result == {"id": row.id, "state": "REJECTED"}
    history = JSON_ROWS.validate_python(row.review["history"], strict=True)
    assert [item["state"] for item in history] == ["IDEA", "REJECTED"]
    assert row.review["gates"] == {"paper_validation": "NOT CONNECTED"}
    assert row.review["evidence"] == [
        {"id": evidence.id, "kind": "alpha", "calculation_version": "alpha-contract"}
    ]


@pytest.mark.parametrize("malformed", [None, [], {"SPY": "bad"}])
def test_invalid_lineage_cannot_mutate_candidate_state_or_history(
    ledger_session: Session,
    malformed: JsonValue,
) -> None:
    row = candidate(ledger_session)
    before = deepcopy(row.review)
    evidence = analysis(ledger_session, "model", {}, {"_datasets": malformed})
    with pytest.raises(HTTPException) as error:
        desks_api.review_candidate(
            row.id,
            desks_api.CandidateReview(
                note="This malformed review must fail",
                state="REJECTED",
                analysis_run_ids=[evidence.id],
            ),
            Request({"type": "http", "headers": []}),
            ledger_session,
        )
    assert error.value.status_code == 422
    assert row.state == "RESEARCH" and row.review == before


@pytest.mark.parametrize("field", ["history", "evidence"])
def test_invalid_saved_review_cannot_mutate_candidate_state(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
) -> None:
    row = candidate(ledger_session)
    row.review = {field: "invalid-recorded-history"}
    before = deepcopy(row.review)
    monkeypatch.setattr(desks_api, "identity", lambda *_: None)
    with pytest.raises(ValueError):
        desks_api.review_candidate(
            row.id,
            desks_api.CandidateReview(note="This review must not change state", state="ARCHIVED"),
            Request({"type": "http", "headers": []}),
            ledger_session,
        )
    assert row.state == "RESEARCH" and row.review == before


def test_equity_uses_latest_base_value_and_unsuperseded_thesis(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime.now(UTC)
    old = analysis(
        ledger_session,
        "thesis",
        {"instrument_id": "AAA", "one_sentence": "Old view", "catalysts": "old"},
    )
    current = analysis(
        ledger_session,
        "thesis",
        {
            "instrument_id": "AAA",
            "parent_id": old.id,
            "one_sentence": "Current view",
            "catalysts": "new",
            "review_date": (now.date() - timedelta(days=1)).isoformat(),
        },
    )
    prior = analysis(
        ledger_session,
        "dcf",
        {
            "instrument_id": "AAA",
            "quality": "ASSUMPTIONS",
            "scenarios": [{"name": "BASE", "fair_value": "140"}],
        },
    )
    prior.created_at = now - timedelta(days=1)
    latest = analysis(
        ledger_session,
        "dcf",
        {
            "instrument_id": "AAA",
            "quality": "ASSUMPTIONS",
            "scenarios": [
                {"name": "BULL", "fair_value": "999"},
                {"name": "BASE", "fair_value": "150"},
            ],
        },
    )
    latest.created_at = now
    internal: dict[str, JsonValue] = {
        "positions": [
            {
                "instrument_id": "AAA",
                "weight": "0.25",
                "market_price": "120",
                "source": "TEST",
                "as_of": "2026-01-07",
            }
        ],
        "source": "TEST",
        "quality": "FILE IMPORT",
        "as_of": "2026-01-07",
    }
    before = deepcopy(internal)
    monkeypatch.setattr(PortfolioValuationService, "latest", lambda *_: internal)
    monkeypatch.setattr(terminal_analytics, "quotes", lambda *_: [{"id": "AAA", "price": 120}])
    result = desks_api.equity(ledger_session)
    coverage = JSON_ROWS.validate_python(result["coverage"], strict=True)
    theses = JSON_ROWS.validate_python(result["theses"], strict=True)
    assert coverage[0]["fair_value"] == "150" and coverage[0]["upside"] == 0.25
    assert coverage[0]["thesis_count"] == 1 and coverage[0]["catalysts"] == "new"
    assert coverage[0]["review_due"] is True
    assert [row["id"] for row in theses] == [current.id]
    assert internal == before
