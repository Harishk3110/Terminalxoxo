"""Capture existing engine results once, including their original lineage."""

from datetime import UTC, datetime

from fastapi.encoders import jsonable_encoder
from pydantic import JsonValue, TypeAdapter
from sqlalchemy.orm import Session

from . import models
from .report_contracts import ANALYSIS_KINDS, FORMATS, ReportRequest, ReportSnapshot, section

JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


def capture(session: Session, request: ReportRequest) -> ReportSnapshot:
    if request.format not in FORMATS[request.kind]:
        raise ValueError("Unsupported report kind/format combination")
    references: dict[str, JsonValue] = {}
    keys: tuple[str, ...]
    currency = "PER_SOURCE"
    if request.kind in ("portfolio", "risk"):
        from .portfolio_resources import PortfolioResourceService

        raw = PortfolioResourceService(session).valuation_snapshot(
            request.portfolio, run_id=request.valuation_run_id, end=request.as_of
        )
        references["portfolio_id"] = raw["portfolio"]["id"]
        references["valuation_run_id"] = raw.get("valuation_run_id")
        currency = str(raw["portfolio"]["base_currency"])
        keys = (
            (
                "portfolio",
                "positions",
                "cash",
                "balance_sheet",
                "reconciliation",
                "performance",
                "curve",
                "transactions",
            )
            if request.kind == "portfolio"
            else ("risk", "risk_model", "exposures", "breaches", "positions", "correlation")
        )
    elif request.kind == "equity":
        from .equity_api import financial_report

        raw = financial_report(session, request.symbol)
        references["symbol"] = request.symbol
        keys = ("items", "ratios", "quote", "lineage")
    elif request.kind == "macro":
        from .services import MacroService

        raw = {
            **MacroService(session).dashboard(),
            "source": "Per-series provenance",
            "quality": "MIXED",
            "currency": "PER_SERIES",
        }
        keys = ("items",)
    else:
        run = (
            session.get(models.AnalysisRun, request.analysis_run_id)
            if request.analysis_run_id
            else None
        )
        if (
            run is None
            or run.status != "SUCCEEDED"
            or not run.result
            or run.kind not in ANALYSIS_KINDS[request.kind]
        ):
            raise ValueError("Select a completed matching analysis run")
        raw = dict(run.result)
        raw["parameters"] = run.parameters
        references = {
            "analysis_run_id": run.id,
            "strategy_id": run.parameters.get("strategy_id"),
            "dataset_version_id": run.parameters.get("dataset_version_id"),
        }
        keys = tuple(key for key in raw if key not in ("source", "quality", "as_of"))
    payload = JSON_OBJECT.validate_python(jsonable_encoder(raw))
    return ReportSnapshot(
        title=f"KnK Capital | {request.kind.title()} Review",
        kind=request.kind,
        requested_at=datetime.now(UTC).isoformat(),
        data_as_of=str(payload["as_of"]) if payload.get("as_of") else None,
        source=str(payload.get("source", "UNVERIFIED")),
        quality=str(payload.get("quality", "UNVERIFIED")),
        currency=str(payload.get("currency", currency)),
        calculation_version=str(
            payload.get("calculation_version", payload.get("version", "UNVERSIONED"))
        ),
        references=references,
        sections=[
            section(key.replace("_", " ").title(), payload[key])
            for key in dict.fromkeys((*keys, "warnings", "methodology", "metric_metadata"))
            if key in payload
        ],
        payload=payload,
    )
