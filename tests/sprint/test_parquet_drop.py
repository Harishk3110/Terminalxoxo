import io
from datetime import date
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from app import models
from app.data_drop import DataDropService
from app.data_mapping import parse_file, seed_profiles
from sqlalchemy import select


def parquet_bytes(rows):
    buffer = io.BytesIO()
    pq.write_table(pa.Table.from_pylist(rows), buffer)
    return buffer.getvalue()


def test_parquet_decimal_date_and_approved_import(ledger_session, tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "object_storage_local_dir", str(tmp_path))
    content = parquet_bytes(
        [{"symbol": "AAA", "date": date(2026, 1, 9), "close": Decimal("123.45678901")}]
    )
    rows, columns = parse_file(content, "prices.parquet")
    assert rows == [{"symbol": "AAA", "date": "2026-01-09", "close": "123.45678901"}]
    assert columns == ["symbol", "date", "close"]
    drop = DataDropService(ledger_session)
    received = drop.receive("prices.parquet", content)
    seed_profiles(ledger_session)
    profile = ledger_session.scalar(
        select(models.MappingProfile).where(models.MappingProfile.code == "KOYFIN_PRICE_HISTORY")
    )
    validated = drop.map_validate(received["id"], profile.id)
    assert validated["state"] == "AWAITING_APPROVAL"
    imported = drop.import_file(
        received["id"],
        name="Koyfin Parquet",
        licence="Internal test fixture",
        approve=True,
        portfolio="book",
    )
    assert imported["state"] == "IMPORTED"
    assert imported["source"] == "KOYFIN FILE"
    assert drop.receive("renamed.parquet", content)["state"] == "DUPLICATE"


def test_parquet_nested_and_oversized_rows_rejected():
    with pytest.raises(ValueError, match="scalar"):
        parse_file(parquet_bytes([{"nested": [1, 2]}]), "bad.parquet")
    with pytest.raises(ValueError, match="100,000"):
        parse_file(parquet_bytes([{"value": 1}] * 100001), "huge.parquet")


def test_jsonl_and_legacy_xls():
    import xlwt

    rows, _ = parse_file(
        b'{"symbol":"AAA","close":120}\n\n{"symbol":"BBB","close":123}\n', "prices.jsonl"
    )
    assert len(rows) == 2
    book = xlwt.Workbook()
    sheet = book.add_sheet("prices")
    for i, row in enumerate([["symbol", "date", "close"], ["AAA", "2026-01-09", 120.25]]):
        for j, value in enumerate(row):
            sheet.write(i, j, value)
    data = io.BytesIO()
    book.save(data)
    rows, _ = parse_file(data.getvalue(), "prices.xls")
    assert rows[0]["close"] == 120.25
    with pytest.raises(ValueError):
        parse_file(b'{"x":1}\nnot-json', "bad.jsonl")
