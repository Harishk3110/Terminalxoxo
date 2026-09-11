"""Import previews must be finite JSON without changing genuine zero or null."""

import io

import pytest
from app import models
from app.data_mapping import parse_file, suggest_mapping
from openpyxl import Workbook
from pydantic import JsonValue


@pytest.mark.parametrize("extension", ["json", "jsonl"])
@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
@pytest.mark.parametrize("nested", [False, True])
def test_nonfinite_json_never_enters_a_preview(extension: str, literal: str, nested: bool) -> None:
    row = '{"close":' + literal + "}"
    if nested:
        row = '{"metadata":[' + row + "]}"
    content = "[" + row + "]" if extension == "json" else row
    with pytest.raises(ValueError):
        parse_file(content.encode(), "invalid." + extension)


@pytest.mark.parametrize(
    "content,filename",
    [
        (b",close\nAAA,12\n", "blank.csv"),
        (b"   ,close\nAAA,12\n", "spaces.csv"),
        (b'[{"":1}]', "blank.json"),
        (b'{"   ":1}', "spaces.jsonl"),
    ],
)
def test_all_formats_require_named_nonempty_headers(content: bytes, filename: str) -> None:
    with pytest.raises(ValueError):
        parse_file(content, filename)


def test_empty_workbook_is_a_validation_error_not_stop_iteration() -> None:
    workbook = Workbook()
    content = io.BytesIO()
    workbook.save(content)
    workbook.close()
    with pytest.raises(ValueError, match="headers"):
        parse_file(content.getvalue(), "empty.xlsx")


@pytest.mark.parametrize("extension", ["json", "jsonl"])
def test_json_values_preserve_zero_null_boolean_and_nested_metadata(extension: str) -> None:
    row = b'{"zero":0,"missing":null,"active":false,"meta":{"tags":["EOD",0]}}'
    content = b"[" + row + b"]" if extension == "json" else row
    rows, columns = parse_file(content, "values." + extension)
    assert rows == [{"zero": 0, "missing": None, "active": False, "meta": {"tags": ["EOD", 0]}}]
    assert columns == ["zero", "missing", "active", "meta"]


def test_workbook_dates_and_decimal_numbers_retain_their_observed_values() -> None:
    from datetime import datetime

    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.append(["date", "close", "volume"])
    sheet.append([datetime(2026, 1, 9), 123.45678901, 0])
    content = io.BytesIO()
    workbook.save(content)
    workbook.close()
    rows, columns = parse_file(content.getvalue(), "prices.xlsx")
    assert rows == [{"date": "2026-01-09T00:00:00", "close": 123.45678901, "volume": 0}]
    assert columns == ["date", "close", "volume"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_parquet_cells_are_rejected(value: float) -> None:
    import pyarrow as pa
    import pyarrow.parquet as pq

    content = io.BytesIO()
    pq.write_table(pa.Table.from_pylist([{"close": value}]), content)
    with pytest.raises(ValueError):
        parse_file(content.getvalue(), "prices.parquet")


@pytest.mark.parametrize("aliases", [None, [], {"symbol": "ticker"}, {"symbol": [1]}])
def test_mapping_aliases_require_named_lists_of_text(aliases: JsonValue) -> None:
    profile = models.MappingProfile(
        code="INVALID", dataset_type="ohlcv", source="EXTERNAL FILE", rules={"aliases": aliases}
    )
    with pytest.raises(ValueError):
        suggest_mapping(["ticker"], profile)
