"""Private equity research: source-pinned valuations and immutable thesis versions."""

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal, Self, TypedDict

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, model_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .equity_financials import comparable_statistics, ratios, statements
from .equity_valuation import DcfRequest, WaccInputs, calculate_wacc, dcf_scenarios
from .portfolio_api import identity
from .portfolio_operations import audit
from .portfolio_resource_api import Database
from .terminal_analytics import fundamentals, history, instrument, quotes

router = APIRouter(prefix="/api/v1/equity", tags=["equity-research"])
ANALYSIS_OBJECT = TypeAdapter(dict[str, JsonValue])
ANALYSIS_SYMBOL = TypeAdapter(str)


class SavedSecurityLink(BaseModel):
    model_config = ConfigDict(strict=True)
    instrument_id: str = Field(min_length=1)


class SavedThesisLink(SavedSecurityLink):
    version: int = Field(default=1, ge=1)


class ThesisHistory(TypedDict):
    items: list[dict[str, JsonValue]]


@router.get("/{symbol}/snapshot")
def security_snapshot(symbol: str, session: Database):
    from .price_sources import MarketPriceResolver

    item = instrument(session, symbol)
    at = datetime.now(UTC)
    resolver = MarketPriceResolver(session, [item.id])
    observation = resolver.resolve(item.id, at)
    price = float(observation.value) if observation else None
    fields = observation.fields or {} if observation else {}
    data = history(session, item.id, 370)
    cutoff = (
        at.date().replace(year=at.year - 1)
        if not (at.month == 2 and at.day == 29)
        else date(at.year - 1, 2, 28)
    ).isoformat()
    actual_bars = [
        row
        for row in data["items"]
        if row["date"] >= cutoff
        and (not row.get("as_of") or str(row["as_of"])[:10] == str(row["date"])[:10])
    ]
    financial = (
        financial_report(session, item.id, quote={"price": price})
        if item.asset_class.upper() == "EQUITY"
        else None
    )
    latest = financial["ratios"][-1] if financial and financial["ratios"] else {}
    quote = {
        key: float(fields[key]) if fields.get(key) is not None else None
        for key in ("bid", "ask", "open", "high", "low", "volume", "vwap")
    }
    quote["last"] = price
    quote["spread"] = (
        quote["ask"] - quote["bid"]
        if quote["ask"] is not None and quote["bid"] is not None and quote["ask"] >= quote["bid"]
        else None
    )
    prior = [
        row
        for row in actual_bars
        if observation and str(row["date"])[:10] < observation.timestamp.date().isoformat()
    ]
    quote["previous_close"] = prior[-1]["close"] if prior else None
    mappings = session.scalars(
        select(models.ProviderInstrumentMapping).where(
            models.ProviderInstrumentMapping.instrument_id == item.id
        )
    ).all()
    return {
        "symbol": item.symbol,
        "name": item.name,
        "sector": item.sector,
        "industry": item.industry,
        "country": item.country,
        "currency": item.currency,
        "asset_class": item.asset_class,
        "figi": item.figi,
        "isin": item.isin,
        "float": None,
        "description": None,
        "beta": None,
        "market_cap": latest.get("market_cap"),
        "enterprise_value": latest.get("enterprise_value"),
        "shares": latest.get("shares"),
        "dividend_yield": latest.get("dividend_yield"),
        "fifty_two_week_low": min(
            (row["low"] for row in actual_bars if row.get("low") is not None), default=None
        ),
        "fifty_two_week_high": max(
            (row["high"] for row in actual_bars if row.get("high") is not None), default=None
        ),
        "quote": quote,
        "provenance": resolver.describe(item.id, at),
        "financial_source": financial["source"] if financial else None,
        "financial_quality": financial["quality"] if financial else None,
        "mappings": [{"provider": row.provider, "symbol": row.provider_symbol} for row in mappings],
        "warnings": [
            "Bid, ask and VWAP require observed provider fields; they are not inferred from daily OHLC. 52-week range covers available observed bars only.",
            "Shares, market cap and EV are in millions; they use the latest available annual actual statement. Float, description and measured beta require source data.",
        ],
    }


def financial_report(
    session: Database,
    symbol: str,
    frequency: str = "ANNUAL",
    actual_estimate: str = "ACTUAL",
    quote: dict[str, object] | None = None,
) -> dict[str, object]:
    item = instrument(session, symbol)
    data = fundamentals(session, item.id)
    selected = statements(data, frequency, actual_estimate)
    quote = (
        quote
        if quote is not None
        else next((row for row in quotes(session) if row["id"] == item.id), {})
    )
    values = []
    for row in selected:
        period = str(row["year"])
        previous_period = str(int(period[:4]) - 1) + period[4:] if period[:4].isdigit() else ""
        previous = next((old for old in selected if str(old["year"]) == previous_period), None)
        calculated = ratios(row, previous, quote.get("price"))
        if frequency == "QUARTERLY":
            for key in (
                "pe",
                "ps",
                "ev_sales",
                "ev_ebitda",
                "ev_ebit",
                "fcf_yield",
                "earnings_yield",
                "dividend_yield",
            ):
                calculated[key] = None
        values.append(calculated)
    return {
        **data,
        "instrument_id": item.id,
        "currency": item.currency,
        "frequency": frequency,
        "actual_estimate": actual_estimate,
        "items": selected,
        "ratios": values,
        "quote": quote,
        "state": "AVAILABLE" if selected else "INSUFFICIENT_DATA",
        "warnings": data.get("warnings", [])
        + [
            "Market multiples use current source-aware price and the selected fiscal period, not historical prices. Historical percentile and forward P/E require aligned verified inputs.",
            "Ratios use positive denominators; ROE/ROA require prior-year average balances. TTM sums four consecutive standalone quarters and uses the final balance sheet/share count.",
            "Segments and after-tax ROIC are unavailable unless a separately validated segment/invested-capital model is supplied.",
        ],
    }


@router.get("/{symbol}/financials")
def financials(
    symbol: str,
    session: Database,
    frequency: Literal["ANNUAL", "QUARTERLY", "TTM"] = "ANNUAL",
    actual_estimate: Literal["ACTUAL", "ESTIMATE"] = "ACTUAL",
):
    return financial_report(session, symbol, frequency, actual_estimate)


def save_analysis(
    session: Session,
    kind: str,
    name: str,
    parameters: Mapping[str, object],
    result: Mapping[str, object],
    actor: str | None,
) -> dict[str, JsonValue]:
    now = datetime.now(UTC)
    parameters = ANALYSIS_OBJECT.validate_python(parameters, strict=True)
    validated_result = ANALYSIS_OBJECT.validate_python(result, strict=True)
    if {"id", "input_hash", "calculated_at"} & validated_result.keys():
        raise ValueError("Analysis result contains reserved receipt metadata")
    encoded = json.dumps(
        {"parameters": parameters, "result": validated_result},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode()
    digest = hashlib.sha256(encoded).hexdigest()
    saved_result: dict[str, JsonValue] = {
        **validated_result,
        "input_hash": digest,
        "calculated_at": now.isoformat(),
    }
    row = models.AnalysisRun(
        kind=kind,
        name=name,
        status="SUCCEEDED",
        parameters=parameters,
        result=saved_result,
        started_at=now,
        finished_at=now,
        history=[{"state": "SUCCEEDED", "at": now.isoformat(), "actor": actor}],
    )
    session.add(row)
    session.flush()
    audit(
        session,
        kind.upper() + "_CREATED",
        "analysis_run",
        row.id,
        {"input_hash": digest},
        actor,
    )
    return ANALYSIS_OBJECT.validate_python({"id": row.id, **saved_result}, strict=True)


@router.post("/dcf", status_code=201)
def calculate_dcf(payload: DcfRequest, request: Request, session: Database):
    actor = identity(request, session)
    item = instrument(session, payload.symbol)
    if item.asset_class.upper() != "EQUITY":
        raise ValueError("Company FCFF valuation requires an equity, not an ETF or derivative")
    if item.sector and "financial" in item.sector.lower():
        raise ValueError(
            "Financial firms require a bank/insurer equity valuation model, not operating-company FCFF"
        )
    financial = financial_report(session, item.id, payload.frequency)
    eligible = [
        row
        for row in financial["items"]
        if not payload.period or str(row["year"]) == payload.period
    ]
    if not eligible:
        raise ValueError("No complete-period actual financial statements are available")
    calculated = dcf_scenarios(eligible[-1], payload, financial["quote"].get("price"))
    result = {
        **calculated,
        "symbol": item.symbol,
        "instrument_id": item.id,
        "currency": item.currency,
        "unit": financial["unit"],
        "source": financial["source"],
        "quality": financial["quality"],
        "as_of": financial["as_of"],
        "quote": financial["quote"],
        "statement_lineage": financial.get("lineage", []),
        "warnings": calculated["warnings"] + financial["warnings"],
    }
    return save_analysis(
        session, "dcf", f"{item.symbol} FCFF", payload.model_dump(mode="json"), result, actor
    )


@router.post("/wacc", status_code=201)
def wacc(payload: WaccInputs, request: Request, session: Database):
    return save_analysis(
        session,
        "wacc",
        "Capital cost assumptions",
        payload.model_dump(mode="json"),
        {
            **calculate_wacc(payload),
            "source": "USER ASSUMPTIONS",
            "quality": "RESEARCH ASSUMPTIONS",
        },
        identity(request, session),
    )


class ComparableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=40)
    peers: list[str] = Field(min_length=1, max_length=20)
    frequency: Literal["ANNUAL", "TTM"] = "ANNUAL"


@router.post("/comparables", status_code=201)
def comparables(payload: ComparableRequest, request: Request, session: Database):
    actor = identity(request, session)
    targets = list(dict.fromkeys([payload.symbol.upper(), *(key.upper() for key in payload.peers)]))
    price_map = {row["symbol"]: row for row in quotes(session)}
    rows, reports = [], []
    for symbol in targets:
        item = instrument(session, symbol)
        if item.asset_class.upper() != "EQUITY":
            raise ValueError("Peer company analysis excludes ETF and derivative instruments")
        report = financial_report(
            session, symbol, payload.frequency, quote=price_map.get(symbol, {})
        )
        reports.append(report)
        rows.append(
            {
                **(report["ratios"][-1] if report["ratios"] else {}),
                "symbol": symbol,
                "currency": item.currency,
                "sector": item.sector,
                "source": report["source"],
                "quality": report["quality"],
                "as_of": report["as_of"],
                "price_as_of": report["quote"].get("as_of"),
            }
        )
    peers = rows[1:]
    if not peers:
        raise ValueError("Select at least one distinct peer other than the target")
    result = {
        "symbol": payload.symbol.upper(),
        "items": rows,
        "statistics": comparable_statistics(peers, rows[0]),
        "inputs": reports,
        "source": "Source-pinned financials and current prices",
        "quality": "MIXED SOURCES"
        if len({r["quality"] for r in reports}) > 1
        else reports[0]["quality"],
        "warnings": [
            "Absolute amounts remain in each company's currency millions; only dimensionless multiples are pooled. Implied valuation is in target currency.",
            "Peers exclude the target from statistics. Positive multiples only; Tukey 1.5-IQR outliers remain included. Small peer sets are not robust sector benchmarks.",
            "Fiscal periods, accounting policies, share-count definitions and source dates may differ; compare the pinned inputs before relying on a multiple.",
        ],
    }
    return save_analysis(
        session,
        "comparables",
        f"{payload.symbol} peers",
        payload.model_dump(mode="json"),
        result,
        actor,
    )


class ThesisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=40)
    parent_id: str | None = None
    title: str = Field(min_length=1, max_length=240)
    one_sentence: str = Field(min_length=1, max_length=500)
    full_thesis: str = Field(default="", max_length=30000)
    variant_perception: str = Field(default="", max_length=5000)
    bull_case: str = Field(default="", max_length=5000)
    base_case: str = Field(default="", max_length=5000)
    bear_case: str = Field(default="", max_length=5000)
    bull_probability: Decimal = Field(default=Decimal(".25"), ge=0, le=1)
    base_probability: Decimal = Field(default=Decimal(".5"), ge=0, le=1)
    bear_probability: Decimal = Field(default=Decimal(".25"), ge=0, le=1)
    fair_value_low: Decimal | None = Field(default=None, ge=0)
    fair_value_high: Decimal | None = Field(default=None, ge=0)
    catalysts: str = Field(default="", max_length=5000)
    risks: str = Field(default="", max_length=5000)
    invalidation: str = Field(default="", max_length=5000)
    monitoring_indicators: str = Field(default="", max_length=5000)
    holding_period: str = Field(default="", max_length=200)
    target_weight: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    maximum_weight: Decimal = Field(default=Decimal(".1"), ge=0, le=1)
    confidence: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"
    review_date: date | None = None
    exit_thesis: str = Field(default="", max_length=5000)
    post_mortem: str = Field(default="", max_length=5000)
    sources: list[str] = Field(default_factory=list, max_length=100)
    attachment_ids: list[str] = Field(default_factory=list, max_length=30)
    dcf_run_id: str | None = None
    state: Literal["DRAFT", "ACTIVE", "REVIEW", "EXITED", "ARCHIVED"] = "DRAFT"

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.bull_probability + self.base_probability + self.bear_probability != 1:
            raise ValueError("Scenario probabilities must sum to one")
        if self.target_weight > self.maximum_weight:
            raise ValueError("Target weight must not exceed maximum weight")
        if (
            self.fair_value_low is not None
            and self.fair_value_high is not None
            and self.fair_value_low > self.fair_value_high
        ):
            raise ValueError("Fair-value range is reversed")
        if any(len(source) > 2000 for source in self.sources):
            raise ValueError("Source citations must be no more than 2,000 characters")
        return self


@router.post("/theses", status_code=201)
def save_thesis(
    payload: ThesisRequest, request: Request, session: Database
) -> dict[str, JsonValue]:
    actor = identity(request, session)
    item = instrument(session, payload.symbol)
    parent = session.get(models.AnalysisRun, payload.parent_id) if payload.parent_id else None
    version = 1
    if payload.parent_id:
        if parent is None or parent.kind != "thesis" or parent.status != "SUCCEEDED":
            raise ValueError("Thesis parent must be a completed saved thesis for this security")
        parent_link = SavedThesisLink.model_validate(parent.result)
        if parent_link.instrument_id != item.id:
            raise ValueError("Thesis parent must be a saved thesis for this security")
        version = parent_link.version + 1
    if payload.dcf_run_id:
        dcf = session.get(models.AnalysisRun, payload.dcf_run_id)
        if (
            dcf is None
            or dcf.kind != "dcf"
            or dcf.status != "SUCCEEDED"
            or SavedSecurityLink.model_validate(dcf.result).instrument_id != item.id
        ):
            raise ValueError("DCF link must be a completed valuation for this security")
    if any(
        session.get(models.UploadedFile, key) is None
        and session.get(models.ExternalFile, key) is None
        for key in payload.attachment_ids
    ):
        raise ValueError("Thesis attachments must reference existing uploaded files")
    result = save_analysis(
        session,
        "thesis",
        payload.title,
        payload.model_dump(mode="json"),
        {
            **payload.model_dump(mode="json"),
            "instrument_id": item.id,
            "source": "PRIVATE USER RESEARCH",
            "quality": "RESEARCH OPINION",
            "version": version,
        },
        actor,
    )
    # One immutable legacy-compatible reference per version keeps ledger links valid.
    session.add(
        models.InvestmentThesis(
            id=result["id"],
            instrument_id=item.id,
            title=payload.title,
            thesis_state=payload.state,
            summary=payload.one_sentence,
        )
    )
    session.flush()
    for citation in payload.sources:
        session.add(
            models.ThesisSource(
                thesis_id=result["id"], source_type="USER CITATION", citation=citation
            )
        )
    for key in payload.attachment_ids:
        uploaded = session.get(models.UploadedFile, key)
        if uploaded is None:
            external = session.get(models.ExternalFile, key)
            uploaded = (
                session.get(models.UploadedFile, external.uploaded_file_id)
                if external and external.uploaded_file_id
                else None
            )
        session.add(
            models.ThesisAttachment(
                thesis_id=result["id"],
                uploaded_file_id=uploaded.id if uploaded else None,
                attachment_type="SOURCE FILE",
                license_notes="User-provided internal research source; original licence applies",
            )
        )
    return result


@router.get("/theses")
def theses(session: Database, symbol: str | None = None) -> ThesisHistory:
    rows = session.scalars(
        select(models.AnalysisRun)
        .where(models.AnalysisRun.kind == "thesis")
        .order_by(models.AnalysisRun.created_at.desc())
        .limit(500)
    ).all()
    items: list[dict[str, JsonValue]] = []
    for row in rows:
        result = ANALYSIS_OBJECT.validate_python(row.result, strict=True)
        if "id" in result:
            raise ValueError("Stored thesis result cannot override receipt identity")
        json.dumps(result, allow_nan=False)
        saved_symbol = ANALYSIS_SYMBOL.validate_python(result.get("symbol", ""), strict=True)
        if not symbol or saved_symbol.upper() == symbol.upper():
            items.append({"id": row.id, **result})
    return {"items": items}
