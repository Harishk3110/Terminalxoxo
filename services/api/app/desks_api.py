"""Research operating views; no synthetic live signals or strategy performance."""

import math
from collections.abc import Mapping
from datetime import UTC, date, datetime
from typing import Annotated, Self

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .database import get_session
from .portfolio_api import identity
from .portfolio_operations import audit
from .portfolio_valuation import PortfolioValuationService
from .terminal_api import run_payload

router = APIRouter(prefix="/api/v1/desks")
Database = Annotated[Session, Depends(get_session)]
JSON_OBJECT = TypeAdapter(dict[str, JsonValue])
JSON_ROWS = TypeAdapter(list[dict[str, JsonValue]])
TEXT = TypeAdapter(str)


def finite_number(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise ValueError("Research metric must be a numeric scalar")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("Research metric must be finite")
    return number


def dataset_versions(parameters: Mapping[str, JsonValue]) -> set[str]:
    versions = set()
    direct = parameters.get("dataset_version_id")
    if direct is not None:
        versions.add(TEXT.validate_python(direct, strict=True))
    datasets = JSON_OBJECT.validate_python(parameters.get("_datasets", {}), strict=True)
    for value in datasets.values():
        dataset = JSON_OBJECT.validate_python(value, strict=True)
        version = dataset.get("dataset_version_id")
        if version is not None:
            versions.add(TEXT.validate_python(version, strict=True))
    return versions


@router.get("/quant")
def quant(session: Database) -> dict[str, JsonValue]:
    runs = session.scalars(
        select(models.AnalysisRun)
        .where(models.AnalysisRun.kind.in_(["backtest", "model", "alpha", "monte_carlo"]))
        .order_by(models.AnalysisRun.created_at.desc())
        .limit(100)
    ).all()
    versions = session.scalars(select(models.StrategyVersion)).all()
    strategies = [
        {
            "id": s.id,
            "name": s.name,
            "type": s.strategy_type,
            "state": "BACKTEST TEMPLATE"
            if s.strategy_type == "moving_average_crossover"
            else "RESEARCH DEFINITION",
            "version": max((v.version for v in versions if v.strategy_id == s.id), default=None),
            "paper_performance": None,
            "live_signals": None,
        }
        for s in session.scalars(select(models.StrategyDefinition)).all()
    ]
    candidates = [
        {
            "id": r.id,
            "name": r.name,
            "hypothesis": r.hypothesis,
            "state": r.state,
            "strategy_id": r.strategy_id,
            "dataset_version_id": r.dataset_version_id,
            "configuration": r.configuration,
            "review": r.review,
        }
        for r in session.scalars(select(models.ResearchCandidate)).all()
    ]
    job_rows = [
        {
            **run_payload(row),
            "runtime_seconds": (row.finished_at - row.started_at).total_seconds()
            if row.finished_at and row.started_at
            else None,
            "stage": row.history[-1].get("message") if row.history else None,
        }
        for row in runs
    ]
    oos = [
        JSON_OBJECT.validate_python(part["metrics"], strict=True)
        for row in runs
        if row.kind == "model" and row.status == "SUCCEEDED"
        for part in JSON_ROWS.validate_python(
            (row.result or {}).get("cost_backtests", []), strict=True
        )
        if part["partition"] == "TEST"
    ]
    summary = {
        "research_strategies": len(strategies),
        "paper_strategies": 0,
        "completed_backtests": sum(
            row.kind == "backtest" and row.status == "SUCCEEDED" for row in runs
        ),
        "failed_backtests": sum(row.kind == "backtest" and row.status == "FAILED" for row in runs),
        "model_runs": sum(row.kind == "model" for row in runs),
        "best_oos_sharpe": max(
            (finite_number(item["sharpe"]) for item in oos if item.get("sharpe") is not None),
            default=None,
        ),
        "queued": sum(row.status == "QUEUED" for row in runs),
        "running": sum(row.status == "RUNNING" for row in runs),
        "scope": "Latest 100 research jobs",
    }
    return JSON_OBJECT.validate_python(
        {
            "strategies": strategies,
            "runs": job_rows,
            "candidates": candidates,
            "summary": summary,
            "signal_state": "HISTORICAL RESEARCH ONLY",
            "paper_state": "NO VERIFIED PAPER PERFORMANCE",
        },
        strict=True,
    )


@router.get("/equity")
def equity(session: Database) -> dict[str, JsonValue]:
    data = PortfolioValuationService(session).latest()
    theses: list[dict[str, JsonValue]] = [
        {
            "id": t.id,
            "title": t.title,
            "instrument_id": t.instrument_id,
            "state": t.thesis_state,
            "summary": t.summary,
        }
        for t in session.scalars(select(models.InvestmentThesis)).all()
    ]
    research = session.scalars(
        select(models.AnalysisRun)
        .where(models.AnalysisRun.kind == "thesis")
        .order_by(models.AnalysisRun.created_at.desc())
        .limit(500)
    ).all()
    saved_theses = [(row, JSON_OBJECT.validate_python(row.result, strict=True)) for row in research]
    superseded = {
        TEXT.validate_python(result["parent_id"], strict=True)
        for _, result in saved_theses
        if result.get("parent_id") is not None
    }
    structured_ids = {row.id for row in research}
    theses = [row for row in theses if row["id"] not in structured_ids]
    theses.extend(
        {
            "id": row.id,
            **result,
            "summary": result.get("one_sentence"),
            "review_due": bool(
                result.get("review_date")
                and date.fromisoformat(TEXT.validate_python(result["review_date"], strict=True))
                <= date.today()
            ),
        }
        for row, result in saved_theses
        if row.id not in superseded
    )
    valuations = session.scalars(
        select(models.AnalysisRun)
        .where(models.AnalysisRun.kind == "dcf", models.AnalysisRun.status == "SUCCEEDED")
        .order_by(models.AnalysisRun.created_at.desc())
        .limit(500)
    ).all()
    targets: dict[str, dict[str, JsonValue]] = {}
    for run in valuations:
        result = JSON_OBJECT.validate_python(run.result, strict=True)
        key = TEXT.validate_python(result["instrument_id"], strict=True)
        if key not in targets:
            base = next(
                (
                    row
                    for row in JSON_ROWS.validate_python(result.get("scenarios", []), strict=True)
                    if row["name"] == "BASE"
                ),
                None,
            )
            if base:
                targets[key] = {
                    "fair_value": base["fair_value"],
                    "valuation_id": run.id,
                    "valuation_quality": result["quality"],
                }
    coverage: list[dict[str, JsonValue]] = []
    for row in JSON_ROWS.validate_python(data["positions"], strict=True):
        item = session.get(
            models.Instrument, TEXT.validate_python(row["instrument_id"], strict=True)
        )
        if item is None:
            raise ValueError("Portfolio holding references a missing instrument")
        files = session.scalars(
            select(models.MarketObservation)
            .where(
                models.MarketObservation.instrument_id == item.id,
                models.MarketObservation.source_category == "FILE",
            )
            .order_by(models.MarketObservation.timestamp.desc())
            .limit(1)
        ).all()
        coverage.append(
            {
                "symbol": item.symbol,
                "name": item.name,
                "sector": item.sector,
                "weight": row["weight"],
                "price": row["market_price"],
                "source": row["source"],
                "as_of": row["as_of"],
                "thesis_count": sum(t["instrument_id"] == item.id for t in theses),
                "review_due": any(
                    t["instrument_id"] == item.id and t.get("review_due") for t in theses
                ),
                "fair_value": targets.get(item.id, {}).get("fair_value"),
                "upside": finite_number(targets[item.id]["fair_value"])
                / finite_number(row["market_price"])
                - 1
                if item.id in targets
                and row["market_price"]
                and finite_number(row["market_price"]) > 0
                else None,
                "valuation_quality": targets.get(item.id, {}).get("valuation_quality"),
                "catalysts": " / ".join(
                    TEXT.validate_python(t["catalysts"], strict=True)
                    for t in theses
                    if t["instrument_id"] == item.id and t.get("catalysts")
                ),
                "latest_file": files[0].fields.get("filename") if files else None,
                "filings_state": "PROVIDER REQUIRED",
                "earnings_state": "PROVIDER REQUIRED",
            }
        )
    from .terminal_analytics import quotes

    universe: list[dict[str, JsonValue]] = []
    for quote in JSON_ROWS.validate_python(quotes(session), strict=True):
        target = targets.get(TEXT.validate_python(quote["id"], strict=True), {})
        universe.append(
            {
                **quote,
                **target,
                "upside": finite_number(target["fair_value"]) / finite_number(quote["price"]) - 1
                if target and quote.get("price") and finite_number(quote["price"]) > 0
                else None,
            }
        )
    return JSON_OBJECT.validate_python(
        {
            "coverage": coverage,
            "theses": theses,
            "universe": universe,
            "summary": {
                "holdings": len(coverage),
                "without_thesis": sum(row["thesis_count"] == 0 for row in coverage),
                "review_due": sum(bool(row.get("review_due")) for row in theses),
                "saved_valuations": len(targets),
            },
            "source": data["source"],
            "quality": data["quality"],
            "as_of": data["as_of"],
        },
        strict=True,
    )


class CandidateConfiguration(BaseModel):
    model_config = ConfigDict(extra="allow")
    economic_rationale: str = Field(default="", max_length=10000)
    universe: list[str] = Field(default_factory=list, max_length=100)
    features: list[str] = Field(default_factory=list, max_length=100)
    target: str = Field(default="", max_length=2000)
    signal_definition: str = Field(default="", max_length=5000)
    position_sizing: str = Field(default="", max_length=2000)
    rebalance_frequency: str = Field(default="DAILY", max_length=30)
    fee_bps: float = Field(default=5, ge=0, le=500, allow_inf_nan=False)
    slippage_bps: float = Field(default=5, ge=0, le=500, allow_inf_nan=False)
    training_start: date | None = None
    training_end: date | None = None
    validation_start: date | None = None
    validation_end: date | None = None
    test_start: date | None = None
    test_end: date | None = None

    @model_validator(mode="after")
    def chronological(self) -> Self:
        dates = [
            self.training_start,
            self.training_end,
            self.validation_start,
            self.validation_end,
            self.test_start,
            self.test_end,
        ]
        selected = [day for day in dates if day is not None]
        if any(right <= left for left, right in zip(selected, selected[1:], strict=False)):
            raise ValueError(
                "Candidate training, validation and test boundaries must be strictly chronological"
            )
        return self


class CandidateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    hypothesis: str = Field(min_length=15, max_length=10000)
    strategy_id: str | None = None
    dataset_version_id: str
    configuration: CandidateConfiguration = Field(default_factory=CandidateConfiguration)


@router.post("/candidates")
def create_candidate(
    payload: CandidateRequest, request: Request, session: Database
) -> dict[str, JsonValue]:
    if session.get(models.DatasetVersion, payload.dataset_version_id) is None:
        raise HTTPException(422, "A persisted dataset version is required")
    if payload.strategy_id and session.get(models.StrategyDefinition, payload.strategy_id) is None:
        raise HTTPException(422, "Unknown strategy")
    row = models.ResearchCandidate(
        **payload.model_dump(mode="json"),
        state="RESEARCH",
        review={
            "gates": {
                "point_in_time": "UNVERIFIED",
                "out_of_sample": "NOT RUN",
                "cost_sensitivity": "NOT RUN",
                "multiple_testing": "NOT REVIEWED",
                "paper_validation": "NOT CONNECTED",
            }
        },
    )
    session.add(row)
    session.flush()
    audit(
        session,
        "RESEARCH_CANDIDATE_CREATED",
        "research_candidate",
        row.id,
        payload.model_dump(mode="json"),
        identity(request, session),
    )
    session.commit()
    return {"id": row.id, "state": row.state, "review": row.review}


class CandidateReview(BaseModel):
    note: str = Field(min_length=10, max_length=10000)
    state: str = "RESEARCH"
    analysis_run_ids: list[str] = Field(default_factory=list, max_length=20)


@router.post("/candidates/{candidate_id}/review")
def review_candidate(
    candidate_id: str, payload: CandidateReview, request: Request, session: Database
) -> dict[str, JsonValue]:
    row = session.get(models.ResearchCandidate, candidate_id)
    if row is None:
        raise HTTPException(404, "Candidate not found")
    if payload.state not in {"IDEA", "RESEARCH", "FAILED_VALIDATION", "REJECTED", "ARCHIVED"}:
        raise HTTPException(
            422,
            "Promotion requires verified OOS and paper-validation gates; no automated promotion is enabled",
        )
    linked: list[JsonValue] = []
    for run_id in payload.analysis_run_ids:
        run = session.get(models.AnalysisRun, run_id)
        if (
            not run
            or run.status != "SUCCEEDED"
            or run.kind not in {"backtest", "model", "alpha", "monte_carlo"}
        ):
            raise HTTPException(422, "Candidate evidence must reference completed research runs")
        try:
            versions = dataset_versions(run.parameters)
            parent_id = run.parameters.get("backtest_run_id")
            if parent_id:
                parent = session.get(
                    models.AnalysisRun, TEXT.validate_python(parent_id, strict=True)
                )
                if parent and parent.kind == "backtest" and parent.status == "SUCCEEDED":
                    versions.update(dataset_versions(parent.parameters))
        except ValueError as exc:
            raise HTTPException(422, "Recorded research dataset lineage is invalid") from exc
        if row.dataset_version_id not in versions:
            raise HTTPException(422, "Evidence must use the candidate's exact dataset version")
        linked.append(
            {
                "id": run.id,
                "kind": run.kind,
                "calculation_version": (run.result or {}).get("calculation_version"),
            }
        )
    actor = identity(request, session)
    history = JSON_ROWS.validate_python(row.review.get("history", []), strict=True)
    evidence = JSON_ROWS.validate_python(row.review.get("evidence", []), strict=True)
    review: dict[str, JsonValue] = {
        "state": payload.state,
        "note": payload.note,
        "actor": actor,
        "at": datetime.now(UTC).isoformat(),
        "evidence": linked,
    }
    row.state = payload.state
    row.review = {
        **row.review,
        "note": payload.note,
        "history": [*history, review],
        "evidence": [*evidence, *linked],
    }
    audit(
        session,
        "RESEARCH_CANDIDATE_REVIEWED",
        "research_candidate",
        row.id,
        payload.model_dump(),
        actor,
    )
    session.commit()
    return {"id": row.id, "state": row.state}
