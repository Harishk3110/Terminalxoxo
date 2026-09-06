"""Private, reproducible alpha analysis of saved portfolio or strategy returns."""

import math
from datetime import UTC, datetime
from typing import Literal

import numpy as np
import pandas as pd
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from . import models
from .alpha_statistics import AlphaSettings, alpha_analysis
from .performance_domain.contracts import FeeBasis, PerformanceSettings
from .portfolio_api import identity
from .portfolio_operations import audit
from .portfolio_performance import PortfolioPerformanceService
from .portfolio_resource_api import Database
from .quant_data import dataset_rows

router = APIRouter(prefix="/api/v1/alpha", tags=["alpha"])


class AlphaRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    portfolio: str = "KNK_MAIN"
    valuation_run_id: str | None = None
    backtest_run_id: str | None = None
    model: Literal["CAPM", "FF3", "FF5", "CARHART", "CUSTOM"] = "CAPM"
    factor_dataset_version_id: str | None = None
    factor_columns: list[str] = Field(default_factory=list, max_length=12)
    factors_are_excess_returns: bool = True
    performance: PerformanceSettings = Field(default_factory=PerformanceSettings)
    regression: AlphaSettings = Field(default_factory=AlphaSettings)
    estimated_cost_bps_per_period: float = Field(default=0, ge=0, le=100, allow_inf_nan=False)


def analyse(session, request: AlphaRequest):
    inputs = {}
    quality, source = "UNAVAILABLE", "UNAVAILABLE"
    eligibility = None
    settings = request.regression.model_copy(
        update={"annual_periods": request.performance.periods_per_year}
    )
    if settings.annual_periods not in {12, 52, 252}:
        raise ValueError("Alpha supports 252 daily, 52 weekly or 12 monthly periods")
    if request.backtest_run_id:
        run = session.get(models.AnalysisRun, request.backtest_run_id)
        if run is None or run.kind != "backtest" or run.status != "SUCCEEDED" or not run.result:
            raise ValueError("A completed saved backtest is required")
        if request.performance.frequency != "DAILY":
            raise ValueError("Saved strategy alpha currently uses daily observations")
        curve = pd.DataFrame(run.result["equity_curve"])
        curve.index = pd.to_datetime(curve["date"])
        if not curve.index.is_unique or not curve.index.is_monotonic_increasing:
            raise ValueError("Saved backtest curve must be daily and chronological")
        net = pd.to_numeric(curve["equity"], errors="raise").pct_change(fill_method=None).iloc[1:]
        benchmark = (
            pd.to_numeric(curve["benchmark"], errors="raise").pct_change(fill_method=None).iloc[1:]
        )
        net = net.loc[request.performance.start : request.performance.end]
        benchmark = benchmark.reindex(net.index)
        gross = pd.Series(np.nan, index=net.index)
        if run.result.get("gross_equity_curve"):
            gross_curve = pd.DataFrame(run.result["gross_equity_curve"])
            gross_curve.index = pd.to_datetime(gross_curve.date)
            gross = (
                pd.to_numeric(gross_curve.equity, errors="raise")
                .pct_change(fill_method=None)
                .reindex(net.index)
            )
        source, quality = run.result["source"], run.result["quality"]
        inputs["backtest_run_id"] = run.id
    else:
        service = PortfolioPerformanceService(session)
        report = service.calculate(
            request.portfolio,
            request.performance.model_copy(update={"fee_basis": FeeBasis.NET}),
            request.valuation_run_id,
        )
        gross_report = service.calculate(
            request.portfolio,
            request.performance.model_copy(update={"fee_basis": FeeBasis.GROSS}),
            report["valuation_run_id"],
        )
        rows = [
            row
            for row in report["series"]
            if (
                request.performance.frequency != "DAILY"
                or datetime.fromisoformat(row["end"]).weekday() < 5
            )
            and row["state"] != "PARTIAL_PERIOD"
        ]
        dates = pd.to_datetime([row["end"] for row in rows])
        net = pd.Series(
            [float(row["value"]) if row["value"] is not None else np.nan for row in rows],
            index=dates,
            dtype=float,
        )
        benchmark = pd.Series(
            [float(row["benchmark"]) if row["benchmark"] is not None else np.nan for row in rows],
            index=dates,
            dtype=float,
        )
        gross_by_date = {row["end"]: row["value"] for row in gross_report["series"]}
        gross = pd.Series(
            [
                float(gross_by_date[row["end"]])
                if gross_by_date.get(row["end"]) is not None
                else np.nan
                for row in rows
            ],
            index=dates,
            dtype=float,
        )
        inputs["valuation_run_id"] = report["valuation_run_id"]
        quality, source = report["source_quality"], "Pinned internal ledger / " + request.portfolio
        if report["summary"]["volatility"]["state"] != "AVAILABLE":
            eligibility = report["summary"]["volatility"]["reason"]
    if len(net) > 5000:
        raise ValueError("Select at most 5,000 return observations")
    annual_rf = float(request.performance.risk_free_rate)
    rf = math.expm1(math.log1p(annual_rf) / settings.annual_periods)
    risk_free = annual_rf
    if request.model == "CAPM":
        factors = pd.DataFrame({"market_excess": benchmark - rf}, index=net.index)
    else:
        if not request.factor_dataset_version_id or not request.factors_are_excess_returns:
            raise ValueError("Factor alpha requires a versioned decimal excess-return dataset")
        rows, provenance = dataset_rows(session, request.factor_dataset_version_id)
        frame = pd.DataFrame(rows)
        if "date" not in frame:
            raise ValueError("Factor returns require an ISO date column")
        frame.index = pd.to_datetime(frame.pop("date"), errors="raise")
        if not frame.index.is_unique or not frame.index.is_monotonic_increasing:
            raise ValueError("Factor dates must be unique and chronological")
        columns = {
            "FF3": ["MKT_RF", "SMB", "HML"],
            "FF5": ["MKT_RF", "SMB", "HML", "RMW", "CMA"],
            "CARHART": ["MKT_RF", "SMB", "HML", "MOM"],
        }.get(request.model, request.factor_columns)
        if not columns or any(column not in frame for column in columns):
            raise ValueError("Required model factor columns are absent from the dataset")
        factors = frame[columns].apply(pd.to_numeric, errors="raise").reindex(net.index)
        if "RF" in frame:
            risk_free = pd.to_numeric(frame["RF"], errors="raise").reindex(net.index)
        inputs["factor_dataset"] = provenance
        source += " / " + provenance["source"]
        quality = quality if quality == provenance["quality"] else "MIXED SOURCES"
    results = {}
    for basis, values in (
        ("NET", net),
        ("GROSS", gross),
        ("NET_AFTER_ESTIMATED_COSTS", net - request.estimated_cost_bps_per_period / 10000),
    ):
        result = alpha_analysis(
            values if eligibility is None else values * np.nan,
            factors,
            settings,
            risk_free,
            benchmark,
        )
        if eligibility:
            result["reason"] = eligibility
        if basis == "GROSS" and request.backtest_run_id and gross.isna().all():
            result["reason"] = "Saved backtest does not record a separate gross counterfactual"
        result["jensen_alpha"] = result["annualised_alpha"] if request.model == "CAPM" else None
        results[basis] = result
    return {
        "model": request.model,
        "source": source,
        "quality": quality,
        "as_of": str(net.index[-1]) if len(net) else None,
        "calculated_at": datetime.now(UTC).isoformat(),
        "calculation_version": "knk-alpha-1.0 / statsmodels 0.15.0",
        "inputs": inputs,
        "settings": request.model_dump(mode="json"),
        "results": results,
        "state": results["NET"]["state"],
        "warnings": [
            "Estimated costs are additional per-period assumptions, not recorded fills or deductions already present in net ledger returns.",
            "Selection/allocation/currency/hedge attribution needs matched benchmark holdings and factor exposures; these are not inferred from aggregate alpha.",
        ],
    }


@router.post("/calculate", status_code=201)
def calculate(payload: AlphaRequest, request: Request, session: Database):
    actor = identity(request, session)
    result = analyse(session, payload)
    now = datetime.now(UTC)
    run = models.AnalysisRun(
        kind="alpha",
        name=f"{payload.model} / {payload.portfolio}",
        status="SUCCEEDED",
        parameters=payload.model_dump(mode="json"),
        result=result,
        started_at=now,
        finished_at=now,
        history=[{"state": "SUCCEEDED", "at": now.isoformat(), "actor": actor}],
    )
    session.add(run)
    session.flush()
    audit(session, "ALPHA_ANALYSIS_CREATED", "analysis_run", run.id, result["inputs"], actor)
    return {"id": run.id, **result}
