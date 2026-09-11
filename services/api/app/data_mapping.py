"""Versioned data-drop mapping profiles and strict tabular normalization."""

import csv
import io
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TypedDict
from zipfile import ZipFile

from pydantic import ConfigDict, JsonValue, TypeAdapter
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .portfolio_engine import decimal

TABULAR_ROWS = TypeAdapter(
    list[dict[str, JsonValue]],
    config=ConfigDict(strict=True, allow_inf_nan=False, hide_input_in_errors=True),
)
PROFILE_ALIASES = TypeAdapter(dict[str, list[str]], config=ConfigDict(strict=True))


class ValidationReport(TypedDict):
    valid: bool
    errors: list[str]
    error_count: int
    warnings: list[str]
    rows: int
    validated_rows: int
    symbol_conflict: bool
    point_in_time: str


ALIASES = {
    "symbol": ["symbol", "ticker", "security", "instrument"],
    "date": ["date", "datetime", "timestamp", "as of", "asof", "period end"],
    "open": ["open", "open price"],
    "high": ["high", "high price"],
    "low": ["low", "low price"],
    "close": ["close", "last", "last price", "price", "close price", "px last"],
    "volume": ["volume", "vol"],
    "currency": ["currency", "ccy", "price currency"],
    "adjusted_close": ["adjusted close", "adj close"],
    "metric": ["metric", "field", "item"],
    "value": ["value", "amount"],
    "period": ["period", "fiscal period"],
    "frequency": ["frequency", "freq"],
    "unit": ["unit", "units"],
    "scale": ["scale", "multiplier"],
    "actual_estimate": ["actual estimate", "actual/estimate", "estimate flag"],
    "report_date": ["report date", "filing date", "available date"],
    "transaction_type": ["transaction type", "type", "action", "side"],
    "trade_date": ["trade date", "date"],
    "settle_date": ["settle date", "settlement date"],
    "quantity": ["quantity", "qty", "shares"],
    "price": ["price", "fill price"],
    "amount": ["amount", "gross amount", "cash amount"],
    "fee": ["fee", "fees"],
    "commission": ["commission", "commissions"],
    "tax": ["tax", "taxes"],
    "fx_rate_to_base": ["fx rate to base", "fx", "exchange rate"],
    "external_reference": ["external reference", "execution id", "trade id", "reference"],
    "base_currency": ["base currency", "base"],
    "quote_currency": ["quote currency", "quote"],
    "rate": ["rate", "fx rate", "exchange rate"],
    "average_cost": ["average cost", "avg cost", "cost price"],
}
SPECS = {
    "GENERIC_OPTIONS_CHAIN": "options_chain",
    "KOYFIN_PRICE_HISTORY": "ohlcv",
    "KOYFIN_EQUITY_SNAPSHOT": "snapshot",
    "KOYFIN_WATCHLIST_EXPORT": "snapshot",
    "KOYFIN_TECHNICAL_EXPORT": "technical",
    "KOYFIN_FUND_EXPORT": "fundamentals_wide",
    "KOYFIN_MACRO_EXPORT": "macro",
    "GENERIC_OHLCV": "ohlcv",
    "GENERIC_FUNDAMENTALS_LONG": "fundamentals_long",
    "GENERIC_FUNDAMENTALS_WIDE": "fundamentals_wide",
    "GENERIC_PORTFOLIO_TRANSACTIONS": "transactions",
    "GENERIC_POSITIONS": "positions",
    "GENERIC_FX_HISTORY": "fx",
}
REQUIRED = {
    "options_chain": [
        "symbol",
        "option_symbol",
        "expiry",
        "strike",
        "right",
        "multiplier",
        "exercise_style",
        "timestamp",
        "iv_unit",
    ],
    "ohlcv": ["date", "close"],
    "snapshot": ["symbol", "close", "date"],
    "technical": ["symbol", "date"],
    "fundamentals_long": ["symbol", "period", "metric", "value"],
    "fundamentals_wide": ["symbol", "period"],
    "macro": ["date", "value"],
    "transactions": ["transaction_type", "trade_date", "currency"],
    "positions": ["symbol", "quantity", "average_cost", "currency"],
    "fx": ["date", "base_currency", "quote_currency", "rate"],
}


def header(value: object) -> str:
    return re.sub(r"[\s_\-]+", " ", str(value).strip().lower())


def seed_profiles(session: Session) -> None:
    existing = set(session.scalars(select(models.MappingProfile.code)).all())
    for code, kind in SPECS.items():
        if code not in existing:
            aliases = ALIASES
            if kind == "options_chain":
                from .options_data import OPTION_ALIASES

                aliases = OPTION_ALIASES
            session.add(
                models.MappingProfile(
                    code=code,
                    version=1,
                    source="KOYFIN FILE" if code.startswith("KOYFIN") else "EXTERNAL FILE",
                    dataset_type=kind,
                    approved=False,
                    rules={
                        "aliases": aliases,
                        "required": REQUIRED[kind],
                        "defaults": {},
                        "auto_import": False,
                        "first_mapping_requires_approval": True,
                    },
                )
            )
    session.flush()


def parse_file(data: bytes, filename: str) -> tuple[list[dict[str, JsonValue]], list[str]]:
    suffix = Path(filename).suffix.lower()
    payload: object
    if suffix == ".xlsx":
        from openpyxl import load_workbook
        from openpyxl.worksheet._read_only import ReadOnlyWorksheet

        with ZipFile(io.BytesIO(data)) as archive:
            if sum(item.file_size for item in archive.infolist()) > 100_000_000:
                raise ValueError("Expanded workbook exceeds 100 MB")
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        try:
            sheet = workbook.active
            if not isinstance(sheet, ReadOnlyWorksheet):
                raise ValueError("Workbook must have an active tabular worksheet")
            iterator = iter(sheet.values)
            columns = [str(v).strip() if v is not None else "" for v in next(iterator, ())]
            if not columns or not all(columns) or len(set(columns)) != len(columns):
                raise ValueError("Workbook headers must be nonempty and unique")
            payload = [
                dict(
                    zip(
                        columns,
                        (v.isoformat() if isinstance(v, (date, datetime)) else v for v in values),
                        strict=True,
                    )
                )
                for values in iterator
                if any(v is not None for v in values)
            ]
        finally:
            workbook.close()
    elif suffix == ".xls":
        import xlrd

        legacy = xlrd.open_workbook(file_contents=data, on_demand=True)
        try:
            legacy_sheet = legacy.sheet_by_index(0)
            if not 1 < legacy_sheet.nrows <= 100001 or legacy_sheet.ncols > 1000:
                raise ValueError("XLS requires at most 100,000 data rows and 1,000 columns")
            columns = [str(value).strip() for value in legacy_sheet.row_values(0)]
            if not all(columns) or len(set(columns)) != len(columns):
                raise ValueError("XLS headers must be nonempty and unique")
            legacy_rows: list[dict[str, object]] = []
            for index in range(1, legacy_sheet.nrows):
                values: list[object] = []
                for cell in legacy_sheet.row(index):
                    if cell.ctype == xlrd.XL_CELL_ERROR:
                        raise ValueError("XLS contains an error cell")
                    value: object = cell.value
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        if not isinstance(value, (int, float)):
                            raise ValueError("XLS contains an invalid date cell")
                        value = xlrd.xldate_as_datetime(value, legacy.datemode).isoformat()
                    values.append(value)
                if any(value not in (None, "") for value in values):
                    legacy_rows.append(dict(zip(columns, values, strict=True)))
            payload = legacy_rows
        finally:
            legacy.release_resources()
    elif suffix == ".jsonl":
        payload = [
            json.loads(line) for line in data.decode("utf-8-sig").splitlines() if line.strip()
        ]
    elif suffix == ".json":
        decoded: object = json.loads(data.decode("utf-8-sig"))
        payload = decoded.get("rows") if isinstance(decoded, dict) else decoded
    elif suffix == ".parquet":
        from decimal import Decimal

        import pyarrow as pa
        import pyarrow.parquet as pq

        parquet = pq.ParquetFile(io.BytesIO(data))
        metadata = parquet.metadata
        if (
            metadata.num_rows > 100000
            or sum(metadata.row_group(i).total_byte_size for i in range(metadata.num_row_groups))
            > 100_000_000
        ):
            raise ValueError("Parquet exceeds 100,000 rows or 100 MB expanded data")
        if len(set(parquet.schema_arrow.names)) != len(parquet.schema_arrow.names):
            raise ValueError("Parquet headers must be unique")
        for field in parquet.schema_arrow:
            if not (
                pa.types.is_string(field.type)
                or pa.types.is_integer(field.type)
                or pa.types.is_floating(field.type)
                or pa.types.is_decimal(field.type)
                or pa.types.is_date(field.type)
                or pa.types.is_timestamp(field.type)
                or pa.types.is_boolean(field.type)
                or pa.types.is_null(field.type)
            ):
                raise ValueError("Parquet requires scalar text, numeric or date columns")
        payload = [
            {
                key: value.isoformat()
                if isinstance(value, (date, datetime))
                else str(value)
                if isinstance(value, Decimal)
                else value
                for key, value in row.items()
            }
            for row in parquet.read().to_pylist()
        ]
    elif suffix == ".csv":
        content = data.decode("utf-8-sig")
        dialect: csv.Dialect | type[csv.Dialect]
        try:
            dialect = csv.Sniffer().sniff(content[:8192], delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(content), dialect=dialect)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError("CSV headers must be unique")
        payload = list(reader)
    else:
        raise ValueError("Supported formats: CSV, XLSX, XLS, JSON, JSONL, Parquet")
    if (
        not isinstance(payload, list)
        or not payload
        or any(
            not isinstance(row, dict)
            or not row
            or any(not isinstance(key, str) or not key.strip() for key in row)
            for row in payload
        )
    ):
        raise ValueError("File must contain nonempty rows with named columns")
    if len(payload) > 100000:
        raise ValueError("Maximum 100,000 rows per file")
    rows = TABULAR_ROWS.validate_python(payload)
    return rows, list(dict.fromkeys(k for r in rows for k in r))


def filename_metadata(filename: str) -> dict[str, str | None]:
    stem = Path(filename).stem
    match = re.match(
        r"^(?P<symbol>[A-Za-z][A-Za-z0-9.]{0,15})[_ -]+(?P<date>\d{4}[-_]?\d{2}[-_]?\d{2})(?:[_ -]+(?P<kind>.+))?$",
        stem,
    )
    if not match:
        return {"symbol": None, "date": None, "type": None}
    token = re.sub(r"\D", "", match["date"])
    try:
        day = date(int(token[:4]), int(token[4:6]), int(token[6:8])).isoformat()
    except ValueError:
        day = None
    return {"symbol": match["symbol"].upper(), "date": day, "type": match["kind"]}


def suggest_mapping(columns: Sequence[str], profile: models.MappingProfile) -> dict[str, str]:
    lookup = {header(c): c for c in columns}
    rules = PROFILE_ALIASES.validate_python(profile.rules.get("aliases"))
    return {
        role: next((lookup[header(alias)] for alias in aliases if header(alias) in lookup), "")
        for role, aliases in rules.items()
        if any(header(alias) in lookup for alias in aliases)
    }


def normalize(
    rows: Sequence[Mapping[str, JsonValue]],
    mapping: Mapping[str, str],
    profile: models.MappingProfile,
    instruments: Sequence[models.Instrument],
    metadata: Mapping[str, JsonValue],
    defaults: Mapping[str, JsonValue],
    resolution: str | None = None,
) -> tuple[list[dict[str, JsonValue]], ValidationReport]:
    kind = profile.dataset_type
    errors: list[str] = []
    warnings: list[str] = []
    normalized: list[dict[str, JsonValue]] = []
    known = {i.symbol: i for i in instruments}
    seen: set[tuple[JsonValue, ...]] = set()
    dates: dict[str, list[date]] = {}
    symbols = {str(r.get(mapping.get("symbol", ""), "")).upper().strip() for r in rows} - {""}
    conflict = metadata.get("symbol") and symbols and symbols != {metadata["symbol"]}
    if conflict and resolution not in {"CONTENT", "FILENAME"}:
        errors.append("Filename/content symbol conflict: explicitly choose CONTENT or FILENAME")
    if resolution == "FILENAME" and len(symbols) > 1:
        errors.append("A multi-security file cannot be assigned to a single filename symbol")
    for index, raw in enumerate(rows, 1):
        row = {role: raw.get(column) for role, column in mapping.items() if column}
        row = {**defaults, **{k: v for k, v in row.items() if v not in (None, "")}}
        if resolution == "FILENAME" or not row.get("symbol"):
            row["symbol"] = metadata.get("symbol") or row.get("symbol")
        if row.get("symbol"):
            row["symbol"] = str(row["symbol"]).upper().strip()
        symbol = str(row["symbol"]) if row.get("symbol") else None
        try:
            for field in REQUIRED[kind]:
                if row.get(field) in (None, ""):
                    raise ValueError(f"Missing {field}")
            if symbol and symbol not in known:
                raise ValueError(f"Unknown security {row['symbol']}")
            item = known.get(symbol) if symbol else None
            if item:
                if row.get("currency") and str(row["currency"]).upper() != item.currency:
                    raise ValueError("Currency differs from security master")
                row["currency"] = item.currency
            for field in ("date", "trade_date", "settle_date", "report_date"):
                if row.get(field):
                    day = date.fromisoformat(str(row[field])[:10])
                    if day > datetime.now(UTC).date():
                        raise ValueError(f"Future {field}")
                    row[field] = day.isoformat()
            key: tuple[JsonValue, ...]
            if kind == "options_chain":
                from .option_contracts import normalize_option

                row = normalize_option(row)
                key = (row["option_symbol"], row["timestamp"])
                warnings.append(
                    "Option expiry time defaults to 20:00 UTC only when not explicitly mapped. Provider Greeks require explicit STANDARD units; options files do not alter ledger positions."
                )
            elif kind in {"ohlcv", "snapshot"}:
                if not item:
                    raise ValueError("Map a security or supply a filename symbol")
                for field in ("open", "high", "low", "close", "adjusted_close"):
                    if row.get(field) not in (None, ""):
                        row[field] = str(decimal(row[field], field, positive=True))
                if row.get("volume") not in (None, ""):
                    row["volume"] = str(decimal(row["volume"], "volume", nonnegative=True))
                if all(row.get(k) is not None for k in ("open", "high", "low", "close")):
                    o, h, low, c = (decimal(row[k]) for k in ("open", "high", "low", "close"))
                    if h < max(o, low, c) or low > min(o, h, c):
                        raise ValueError("Invalid OHLC high/low ordering")
                else:
                    warnings.append(
                        "Incomplete OHLC: close-only prices can value NAV but cannot run OHLC backtests"
                    )
                key = (row["symbol"], row["date"])
                dates.setdefault(str(row["symbol"]), []).append(
                    date.fromisoformat(str(row["date"]))
                )
            elif kind == "fx":
                currencies = (
                    str(row["base_currency"]).upper(),
                    str(row["quote_currency"]).upper(),
                )
                row["base_currency"], row["quote_currency"] = currencies
                if any(len(code) != 3 or not code.isalpha() for code in currencies):
                    raise ValueError("FX currencies must be three-letter codes")
                row["rate"] = str(decimal(row["rate"], "rate", positive=True))
                if row["base_currency"] == row["quote_currency"] and decimal(row["rate"]) != 1:
                    raise ValueError("Identity FX must equal one")
                key = (row["base_currency"], row["quote_currency"], row["date"])
            elif kind.startswith("fundamentals"):
                for field in ("frequency", "unit", "scale", "actual_estimate", "report_date"):
                    if not row.get(field):
                        raise ValueError(f"Fundamentals require explicit {field}")
                if str(row["actual_estimate"]).upper() not in {"ACTUAL", "ESTIMATE"}:
                    raise ValueError("actual_estimate must be ACTUAL or ESTIMATE")
                row["scale"] = str(decimal(row["scale"], "scale", positive=True))
                if kind == "fundamentals_long":
                    row["value"] = str(decimal(row["value"], "value"))
                else:
                    excluded = set(mapping.values())
                    metrics = {
                        k: str(decimal(v, k))
                        for k, v in raw.items()
                        if k not in excluded and v not in (None, "")
                    }
                    if not metrics:
                        raise ValueError("No numeric fundamental metrics")
                    row["metrics"] = {**metrics}
                key = (row["symbol"], str(row["period"]), row.get("metric"), row["actual_estimate"])
            elif kind == "transactions":
                from .portfolio_engine import TRANSACTION_TYPES

                row["transaction_type"] = str(row["transaction_type"]).upper()
                if row["transaction_type"] not in TRANSACTION_TYPES:
                    raise ValueError("Unknown ledger transaction type")
                for field in (
                    "quantity",
                    "price",
                    "amount",
                    "fee",
                    "commission",
                    "tax",
                    "fx_rate_to_base",
                ):
                    if row.get(field) not in (None, ""):
                        row[field] = str(decimal(row[field], field, nonnegative=True))
                key = (
                    ("reference", row["external_reference"])
                    if row.get("external_reference")
                    else ("row", json.dumps(row, sort_keys=True))
                )
            else:
                if kind == "positions":
                    row["quantity"], row["average_cost"] = (
                        str(decimal(row["quantity"])),
                        str(decimal(row["average_cost"], positive=True)),
                    )
                    warnings.append(
                        "Position files are reconciliation references only; positions remain ledger-derived"
                    )
                key = ("row", json.dumps(row, sort_keys=True))
            if key in seen:
                raise ValueError("Duplicate instrument/date or record within file")
            seen.add(key)
            normalized.append(row)
        except (ValueError, TypeError, KeyError) as exc:
            errors.append(f"Row {index}: {exc}")
    for symbol, values in dates.items():
        ordered = sorted(values)
        if values != ordered:
            warnings.append(f"{symbol}: dates were sorted during import")
        if any((b - a).days > 7 for a, b in zip(ordered, ordered[1:], strict=False)):
            warnings.append(f"{symbol}: price gaps exceed seven calendar days")
    return normalized, {
        "valid": not errors,
        "errors": errors[:100],
        "error_count": len(errors),
        "warnings": list(dict.fromkeys(warnings)),
        "rows": len(rows),
        "validated_rows": len(normalized),
        "symbol_conflict": bool(conflict),
        "point_in_time": "UNVERIFIED",
    }
