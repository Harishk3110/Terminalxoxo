"""Private options calculations from immutable imported or explicit demo chains."""

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from . import models
from .config import get_settings
from .equity_api import save_analysis
from .object_storage import ObjectStorage
from .option_contracts import ChainContract
from .option_greeks import PricingInputs, greeks
from .options_analytics import OptionLeg, OptionsRequest, analyse_chain, position_analytics
from .options_data import chain_versions, load_chain
from .portfolio_api import identity
from .portfolio_operations import audit
from .portfolio_resource_api import Database
from .portfolio_valuation import PortfolioValuationService
from .price_sources import MarketPriceResolver
from .terminal_analytics import instrument

router = APIRouter(prefix="/api/v1/options", tags=["options-research"])


@router.get("/datasets")
def datasets(session: Database):
    return {"items": chain_versions(session)}


@router.get("/datasets/{version_id}")
def dataset(version_id: str, session: Database):
    rows, provenance = load_chain(session, version_id)
    return {
        "items": [row.model_dump(mode="json") for row in rows],
        "provenance": provenance,
        "as_of": max(row.timestamp for row in rows).isoformat(),
        "symbols": sorted({row.symbol for row in rows}),
    }


@router.post("/calculate", status_code=201)
def calculate(payload: OptionsRequest, request: Request, session: Database):
    actor = identity(request, session)
    item = instrument(session, payload.symbol)
    payload = payload.model_copy(update={"symbol": item.symbol})
    if payload.portfolio and payload.legs:
        raise ValueError("Select internal-ledger positions or hypothetical legs, not both")
    if payload.dataset_version_id:
        contracts, provenance = load_chain(session, payload.dataset_version_id)
    else:
        contracts, provenance = [], {}
        for version in chain_versions(session):
            candidates, meta = load_chain(session, version["id"])
            if any(row.symbol == item.symbol for row in candidates):
                contracts, provenance = candidates, meta
                break
        if not contracts:
            raise ValueError(
                "DATA UNAVAILABLE: import an options chain or explicitly create a demo dataset"
            )
    as_of = payload.as_of or datetime.now(UTC)
    if as_of.tzinfo is None:
        raise ValueError("As-of requires an explicit timezone")
    resolver = MarketPriceResolver(session, [item.id])
    selected = resolver.resolve(item.id, as_of)
    price_source = resolver.describe(item.id, as_of)
    if payload.spot_override is not None:
        spot = payload.spot_override
        price_source = {
            "source": "USER SPOT ASSUMPTION",
            "value": str(spot),
            "as_of": as_of.isoformat(),
            "data_state": "RESEARCH ASSUMPTION",
        }
    elif selected is not None and not price_source.get("stale"):
        spot = float(selected.value)
    else:
        raise ValueError(
            "Current eligible spot is unavailable or stale; import a price or set an explicit spot assumption"
        )
    result = analyse_chain(contracts, payload, spot, as_of)
    if result["currency"] != item.currency:
        raise ValueError("Option chain currency must match selected underlying currency")
    result.update(
        {
            "source": provenance["source"],
            "quality": provenance["quality"],
            "inputs": provenance,
            "spot_provenance": price_source,
            "instrument_id": item.id,
        }
    )
    legs = payload.legs
    equity_quantity = 0
    if payload.portfolio:
        valuation = PortfolioValuationService(session).latest(payload.portfolio, end=as_of.date())
        result["valuation_run_id"] = valuation["valuation_run_id"]
        instruments = {row.id: row for row in session.scalars(select(models.Instrument)).all()}
        options = {row.option_symbol for row in contracts if row.symbol == item.symbol}
        legs = []
        unmatched = []
        for position in valuation["positions"]:
            held = instruments.get(position["instrument_id"])
            if held is None:
                continue
            if held.id == item.id:
                equity_quantity += float(position["quantity"])
            elif held.symbol in options:
                legs.append(
                    OptionLeg(option_symbol=held.symbol, quantity=float(position["quantity"]))
                )
            elif held.asset_class.upper() in {"OPTION", "OPTIONS"}:
                unmatched.append(held.symbol)
        result["unmatched_portfolio_options"] = unmatched
        result["position_source"] = "INTERNAL LEDGER / SELECTED UNDERLYING"
        result["warnings"].append(
            "Ledger option quantities are interpreted as contract counts. Unmatched option positions and other underlyings are excluded and listed; this is not a complete multi-currency portfolio risk report."
        )
    else:
        result["position_source"] = "HYPOTHETICAL LEGS / NOT LEDGER TRANSACTIONS"
    result["positions"] = position_analytics(result, legs, equity_quantity)
    pinned_parameters = {
        **payload.model_dump(mode="json"),
        "dataset_version_id": provenance["dataset_version_id"],
        "as_of": as_of.isoformat(),
    }
    return save_analysis(
        session,
        "options",
        f"{item.symbol} options / {payload.dealer_sign}",
        pinned_parameters,
        result,
        actor,
    )


class DemoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    symbol: str = Field(min_length=1, max_length=40)
    spot: float = Field(default=100, gt=1, le=100000)


@router.post("/demo", status_code=201)
def demo(payload: DemoRequest, request: Request, session: Database):
    actor = identity(request, session)
    if get_settings().knk_env not in {"local-demo", "demo", "test"}:
        raise ValueError("Demo-chain generation is disabled in production")
    item = instrument(session, payload.symbol)
    now = datetime.now(UTC).replace(microsecond=0)
    rows = []
    for days in (30, 60, 90):
        expiry = (now + timedelta(days=days)).date()
        for index, ratio in enumerate((0.8, 0.9, 1, 1.1, 1.2)):
            strike = round(payload.spot * ratio, 4)
            for right in ("CALL", "PUT"):
                option_symbol = f"DEMO.{item.symbol}.{expiry}.{right[0]}.{strike}"
                contract = ChainContract(
                    symbol=item.symbol,
                    option_symbol=option_symbol,
                    expiry=expiry,
                    strike=strike,
                    right=right,
                    multiplier=100,
                    exercise_style="EUROPEAN",
                    currency=item.currency,
                    timestamp=now,
                    iv_unit="DECIMAL",
                    iv=0.22 + abs(ratio - 1) * 0.3,
                    open_interest=100 + index * 80 + (140 if right == "PUT" and ratio < 1 else 0),
                    volume=20 + index * 10,
                )
                inputs = PricingInputs(
                    right=right,
                    spot=payload.spot,
                    strike=strike,
                    years=(contract.expires_at - now).total_seconds() / (365 * 86400),
                    volatility=contract.iv,
                )
                price = greeks(inputs, advanced=False)["theoretical_price"]
                contract.bid = max(0, price - 0.03)
                contract.ask = price + 0.03
                contract.last = price
                rows.append(contract.model_dump(mode="json"))
    content = json.dumps(rows, sort_keys=True, allow_nan=False).encode()
    digest = hashlib.sha256(content).hexdigest()
    key = f"options-demo/{uuid.uuid4()}/{digest}.json"
    ObjectStorage().put_bytes(key=key, data=content, content_type="application/json")
    dataset = models.Dataset(
        name=f"DEMO {item.symbol} European options",
        dataset_type="options_chain",
        source="KnK synthetic option fixture",
        quality="DEMO DATA",
    )
    raw = models.RawObject(
        provider="KnK synthetic option fixture",
        dataset="options_chain",
        object_key=key,
        content_hash=digest,
        content_type="application/json",
        size_bytes=len(content),
        correlation_id=digest,
    )
    session.add_all([dataset, raw])
    session.flush()
    version = models.DatasetVersion(
        dataset_id=dataset.id,
        version=1,
        raw_object_id=raw.id,
        row_count=len(rows),
        content_hash=digest,
        schema_json={
            "curated_key": key,
            "curated_hash": digest,
            "quality": "DEMO DATA",
            "spot_reference": payload.spot,
            "symbol": item.symbol,
            "source": "KnK synthetic option fixture",
        },
    )
    session.add(version)
    session.flush()
    session.add(
        models.DatasetLineage(
            dataset_version_id=version.id,
            source_type="EXPLICIT_DEMO_GENERATION",
            source_id=item.id,
            transform="BSM-generated synthetic European option fixture; never observed exchange quotes",
        )
    )
    audit(
        session,
        "DEMO_OPTION_CHAIN_CREATED",
        "dataset_version",
        version.id,
        {"symbol": item.symbol, "spot": payload.spot, "hash": digest},
        actor,
    )
    return {
        "id": version.id,
        "source": dataset.source,
        "quality": dataset.quality,
        "spot": payload.spot,
        "as_of": now.isoformat(),
        "rows": len(rows),
    }
