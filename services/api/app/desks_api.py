"""Research operating views; no synthetic live signals or strategy performance."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from . import models
from .database import get_session
from .portfolio_api import identity
from .portfolio_operations import audit
from .portfolio_valuation import PortfolioValuationService
from .terminal_api import run_payload

router = APIRouter(prefix="/api/v1/desks")


@router.get("/quant")
def quant(session: Session = Depends(get_session)):
    runs = session.scalars(select(models.AnalysisRun).order_by(models.AnalysisRun.created_at.desc()).limit(50)).all()
    versions = session.scalars(select(models.StrategyVersion)).all()
    strategies = [{"id": s.id, "name": s.name, "type": s.strategy_type, "state": "BACKTEST TEMPLATE" if s.strategy_type == "moving_average_crossover" else "RESEARCH DEFINITION", "version": max((v.version for v in versions if v.strategy_id == s.id), default=None), "paper_performance": None, "live_signals": None} for s in session.scalars(select(models.StrategyDefinition)).all()]
    candidates = [{"id": r.id, "name": r.name, "hypothesis": r.hypothesis, "state": r.state, "strategy_id": r.strategy_id, "dataset_version_id": r.dataset_version_id, "configuration": r.configuration, "review": r.review} for r in session.scalars(select(models.ResearchCandidate)).all()]
    return {"strategies": strategies, "runs": [run_payload(r) for r in runs], "candidates": candidates, "signal_state": "NOT CONNECTED", "paper_state": "NO VERIFIED PAPER PERFORMANCE"}


@router.get("/equity")
def equity(session: Session = Depends(get_session)):
    data = PortfolioValuationService(session).latest()
    theses = [{"id": t.id, "title": t.title, "instrument_id": t.instrument_id, "state": t.thesis_state, "summary": t.summary} for t in session.scalars(select(models.InvestmentThesis)).all()]
    coverage = []
    for row in data["positions"]:
        item = session.get(models.Instrument, row["instrument_id"])
        files = session.scalars(select(models.MarketObservation).where(models.MarketObservation.instrument_id == item.id, models.MarketObservation.source_category == "FILE").order_by(models.MarketObservation.timestamp.desc()).limit(1)).all()
        coverage.append({"symbol": item.symbol, "name": item.name, "sector": item.sector, "weight": row["weight"], "price": row["market_price"], "source": row["source"], "as_of": row["as_of"], "thesis_count": sum(t["instrument_id"] == item.id for t in theses), "latest_file": files[0].fields.get("filename") if files else None, "filings_state": "PROVIDER REQUIRED", "earnings_state": "PROVIDER REQUIRED"})
    return {"coverage": coverage, "theses": theses, "source": data["source"], "quality": data["quality"], "as_of": data["as_of"]}


class CandidateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    hypothesis: str = Field(min_length=15, max_length=10000)
    strategy_id: str | None = None
    dataset_version_id: str
    configuration: dict = Field(default_factory=dict)


@router.post("/candidates")
def create_candidate(payload: CandidateRequest, request: Request, session: Session = Depends(get_session)):
    if session.get(models.DatasetVersion, payload.dataset_version_id) is None:
        raise HTTPException(422, "A persisted dataset version is required")
    if payload.strategy_id and session.get(models.StrategyDefinition, payload.strategy_id) is None:
        raise HTTPException(422, "Unknown strategy")
    row = models.ResearchCandidate(**payload.model_dump(), state="RESEARCH", review={"gates": {"point_in_time": "UNVERIFIED", "out_of_sample": "NOT RUN", "cost_sensitivity": "NOT RUN", "multiple_testing": "NOT REVIEWED", "paper_validation": "NOT CONNECTED"}})
    session.add(row)
    session.flush()
    audit(session, "RESEARCH_CANDIDATE_CREATED", "research_candidate", row.id, payload.model_dump(), identity(request, session))
    session.commit()
    return {"id": row.id, "state": row.state, "review": row.review}


class CandidateReview(BaseModel):
    note: str = Field(min_length=10, max_length=10000)
    state: str = "RESEARCH"


@router.post("/candidates/{candidate_id}/review")
def review_candidate(candidate_id: str, payload: CandidateReview, request: Request, session: Session = Depends(get_session)):
    row = session.get(models.ResearchCandidate, candidate_id)
    if row is None:
        raise HTTPException(404, "Candidate not found")
    if payload.state not in {"RESEARCH", "REJECTED", "ARCHIVED"}:
        raise HTTPException(422, "Promotion requires verified OOS and paper-validation gates; no automated promotion is enabled")
    row.state = payload.state
    row.review = {**row.review, "note": payload.note}
    audit(session, "RESEARCH_CANDIDATE_REVIEWED", "research_candidate", row.id, payload.model_dump(), identity(request, session))
    session.commit()
    return {"id": row.id, "state": row.state}
