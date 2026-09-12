"""Immutable option-chain dataset discovery and validated file normalization."""

from datetime import datetime

from pydantic import TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .option_contracts import ChainContract
from .options_results import ChainVersion
from .quant_data import DatasetProvenance, dataset_rows

OPTIONAL_FILE_ID: TypeAdapter[str | None] = TypeAdapter(str | None)

OPTION_ALIASES = {
    "symbol": ["underlying", "underlying symbol", "underlying ticker"],
    "option_symbol": ["option symbol", "contract symbol", "option ticker", "contract"],
    "expiry": ["expiry", "expiration", "expiration date", "expiry date"],
    "expiry_time_utc": ["expiry time utc", "expiration time utc"],
    "strike": ["strike", "strike price"],
    "right": ["right", "call put", "option type", "put call"],
    "multiplier": ["contract multiplier", "multiplier", "contract size"],
    "exercise_style": ["exercise style", "exercise", "style"],
    "currency": ["currency", "ccy"],
    "timestamp": ["timestamp", "as of", "asof", "quote timestamp"],
    "iv_unit": ["iv unit", "volatility unit"],
    "iv": ["iv", "implied volatility"],
    "bid": ["bid", "bid price"],
    "ask": ["ask", "ask price"],
    "last": ["last", "last price"],
    "volume": ["volume", "vol"],
    "open_interest": ["open interest", "oi"],
    "oi_change": ["oi change", "open interest change"],
    **{name: [name] for name in ("delta", "gamma", "theta", "vega", "rho")},
    "greek_units": ["greek units", "greeks units"],
}


def chain_versions(session: Session, symbol: str | None = None) -> list[ChainVersion]:
    rows = session.execute(
        select(models.DatasetVersion, models.Dataset)
        .join(models.Dataset, models.Dataset.id == models.DatasetVersion.dataset_id)
        .where(models.Dataset.dataset_type == "options_chain")
        .order_by(models.DatasetVersion.created_at.desc())
        .limit(100)
    ).all()
    items: list[ChainVersion] = []
    for version, dataset in rows:
        schema = version.schema_json or {}
        items.append(
            {
                "id": version.id,
                "dataset_id": dataset.id,
                "name": dataset.name,
                "version": version.version,
                "source": dataset.source,
                "quality": dataset.quality,
                "rows": version.row_count,
                "created_at": version.created_at.isoformat(),
                "file_id": OPTIONAL_FILE_ID.validate_python(schema.get("file_id"), strict=True),
            }
        )
    return items


def load_chain(session: Session, version_id: str) -> tuple[list[ChainContract], DatasetProvenance]:
    version = session.get(models.DatasetVersion, version_id)
    dataset = session.get(models.Dataset, version.dataset_id) if version else None
    if dataset is None or dataset.dataset_type != "options_chain":
        raise ValueError("A persisted options-chain dataset is required")
    rows, provenance = dataset_rows(session, version_id)
    if not rows or len(rows) > 2000:
        raise ValueError("Options research supports one to 2,000 contracts per version")
    contracts = [ChainContract.model_validate(row) for row in rows]
    seen: set[tuple[str, datetime]] = set()
    for contract in contracts:
        key = (contract.option_symbol, contract.timestamp)
        if key in seen:
            raise ValueError("Duplicate option symbol and timestamp in source version")
        seen.add(key)
    return contracts, provenance
