"""Research operating views; no synthetic live signals or strategy performance."""

from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
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


@router.get("/quant")
def quant(session: Database):
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
        part["metrics"]
        for row in runs
        if row.kind == "model" and row.status == "SUCCEEDED"
        for part in (row.result or {}).get("cost_backtests", [])
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
            (item["sharpe"] for item in oos if item.get("sharpe") is not None), default=None
        ),
        "queued": sum(row.status == "QUEUED" for row in runs),
        "running": sum(row.status == "RUNNING" for row in runs),
        "scope": "Latest 100 research jobs",
    }
    return {
        "strategies": strategies,
        "runs": job_rows,
        "candidates": candidates,
        "summary": summary,
        "signal_state": "HISTORICAL RESEARCH ONLY",
        "paper_state": "NO VERIFIED PAPER PERFORMANCE",
    }


@router.get("/equity")
def equity(session: Database):
    data = PortfolioValuationService(session).latest()
    theses = [
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
    superseded = {row.result.get("parent_id") for row in research}
    structured_ids = {row.id for row in research}
    theses = [row for row in theses if row["id"] not in structured_ids]
    theses.extend(
        {
            "id": row.id,
            **row.result,
            "summary": row.result.get("one_sentence"),
            "review_due": bool(
                row.result.get("review_date")
                and row.result["review_date"] <= date.today().isoformat()
            ),
        }
        for row in research
        if row.id not in superseded
    )
    valuations = session.scalars(
        select(models.AnalysisRun)
        .where(models.AnalysisRun.kind == "dcf", models.AnalysisRun.status == "SUCCEEDED")
        .order_by(models.AnalysisRun.created_at.desc())
        .limit(500)
    ).all()
    targets = {}
    for run in valuations:
        key = run.result.get("instrument_id")
        if key not in targets:
            base = next(
                (row for row in run.result.get("scenarios", []) if row["name"] == "BASE"), None
            )
            if base:
                targets[key] = {
                    "fair_value": base["fair_value"],
                    "valuation_id": run.id,
                    "valuation_quality": run.result["quality"],
                }
    coverage = []
    for row in data["positions"]:
        item = session.get(models.Instrument, row["instrument_id"])
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
                "upside": float(targets[item.id]["fair_value"]) / float(row["market_price"]) - 1
                if item.id in targets and row["market_price"] and float(row["market_price"]) > 0
                else None,
                "valuation_quality": targets.get(item.id, {}).get("valuation_quality"),
                "catalysts": " / ".join(
                    t.get("catalysts", "")
                    for t in theses
                    if t["instrument_id"] == item.id and t.get("catalysts")
                ),
                "latest_file": files[0].fields.get("filename") if files else None,
                "filings_state": "PROVIDER REQUIRED",
                "earnings_state": "PROVIDER REQUIRED",
            }
        )
    from .terminal_analytics import quotes

    universe = []
    for quote in quotes(session):
        target = targets.get(quote["id"], {})
        universe.append(
            {
                **quote,
                **target,
                "upside": float(target["fair_value"]) / quote["price"] - 1
                if target and quote.get("price") and quote["price"] > 0
                else None,
            }
        )
    return {
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
    }


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
    def chronological(self):
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
def create_candidate(payload: CandidateRequest, request: Request, session: Database):
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
):
    row = session.get(models.ResearchCandidate, candidate_id)
    if row is None:
        raise HTTPException(404, "Candidate not found")
    if payload.state not in {"IDEA", "RESEARCH", "FAILED_VALIDATION", "REJECTED", "ARCHIVED"}:
        raise HTTPException(
            422,
            "Promotion requires verified OOS and paper-validation gates; no automated promotion is enabled",
        )
    linked = []
    for run_id in payload.analysis_run_ids:
        run = session.get(models.AnalysisRun, run_id)
        if (
            not run
            or run.status != "SUCCEEDED"
            or run.kind not in {"backtest", "model", "alpha", "monte_carlo"}
        ):
            raise HTTPException(422, "Candidate evidence must reference completed research runs")
        versions = {run.parameters.get("dataset_version_id")}
        versions.update(
            value.get("dataset_version_id")
            for value in run.parameters.get("_datasets", {}).values()
        )
        parent_id = run.parameters.get("backtest_run_id")
        if parent_id:
            parent = session.get(models.AnalysisRun, parent_id)
            if parent and parent.kind == "backtest" and parent.status == "SUCCEEDED":
                versions.add(parent.parameters.get("dataset_version_id"))
                versions.update(
                    value.get("dataset_version_id")
                    for value in parent.parameters.get("_datasets", {}).values()
                )
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
    row.state = payload.state
    review = {
        "state": payload.state,
        "note": payload.note,
        "actor": actor,
        "at": datetime.now(UTC).isoformat(),
        "evidence": linked,
    }
    row.review = {
        **row.review,
        "note": payload.note,
        "history": [*row.review.get("history", []), review],
        "evidence": [*row.review.get("evidence", []), *linked],
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
