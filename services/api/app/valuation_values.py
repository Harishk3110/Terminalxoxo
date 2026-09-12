"""Exact financial values at the valuation JSON boundary."""

import math
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import overload

from pydantic import JsonValue


@overload
def jsonable(value: Mapping[str, object]) -> dict[str, JsonValue]: ...


@overload
def jsonable(value: object) -> JsonValue: ...


def jsonable(value: object) -> JsonValue:
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Financial decimal output must be finite")
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Financial JSON keys must be strings")
            result[key] = jsonable(item)
        return result
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Financial numeric output must be finite")
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise ValueError("Financial output contains an unsupported JSON value")


def number(value: Decimal | float | int | str | None) -> float | None:
    if value is None:
        return None
    result = float(value)
    return result if math.isfinite(result) else None
