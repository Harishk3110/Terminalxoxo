"""Bounded read-only provider transport; errors never contain credentials or bodies."""

import asyncio
import json
import math
import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Never

import httpx
from pydantic import ConfigDict, JsonValue, TypeAdapter, ValidationError

type QueryParams = Mapping[str, str | int | float | bool | None]
JSON_RESPONSE = TypeAdapter[JsonValue](
    JsonValue, config=ConfigDict(strict=True, allow_inf_nan=False)
)


def _reject_constant(value: str) -> Never:
    raise ValueError("Non-finite JSON constant")


def _finite_float(value: str) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("JSON number exceeds finite range")
    return number


class ProviderError(ValueError):
    def __init__(
        self,
        message: str,
        state: str = "FAILED",
        status_code: int | None = None,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.state = state
        self.status_code = status_code
        self.retry_after = retry_after


@dataclass
class Response:
    payload: dict[str, JsonValue] | list[JsonValue]
    content: bytes
    url: str
    latency_ms: int
    rate_remaining: str | None


_lock = threading.Lock()
_next_request: dict[str, float] = {}


async def pace(name: str, interval: float) -> None:
    # Reserve globally across adapter instances in this API process.
    with _lock:
        now = time.monotonic()
        scheduled = max(now, _next_request.get(name, now))
        _next_request[name] = scheduled + interval
    await asyncio.sleep(max(0, scheduled - now))


async def fetch(
    name: str,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    params: QueryParams | None = None,
    body: JsonValue = None,
    interval: float = 0.25,
    transport: httpx.AsyncBaseTransport | None = None,
    timeout: float = 20,
    attempts: int = 3,
) -> Response:
    headers = headers or {}
    for attempt in range(attempts):
        await pace(name, interval)
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=timeout, transport=transport, follow_redirects=False
            ) as client:
                async with client.stream(
                    "POST" if body is not None else "GET",
                    url,
                    headers=headers,
                    params=params,
                    json=body,
                ) as response:
                    code = response.status_code
                    if code == 429:
                        raise ProviderError(
                            f"{name} rate limited",
                            "RATE_LIMITED",
                            code,
                            response.headers.get("retry-after"),
                        )
                    if code >= 500 and attempt < attempts - 1:
                        await asyncio.sleep(2**attempt)
                        continue
                    if code != 200:
                        raise ProviderError(f"{name} HTTP {code}", status_code=code)
                    chunks, size = [], 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > 25_000_000:
                            raise ProviderError(f"{name} response exceeds 25 MB")
                        chunks.append(chunk)
                    content = b"".join(chunks)
                    try:
                        # JsonValue itself accepts NaN; reject constants and exponent overflow.
                        payload = JSON_RESPONSE.validate_python(
                            json.loads(
                                content, parse_constant=_reject_constant, parse_float=_finite_float
                            )
                        )
                    except (ValidationError, ValueError, UnicodeDecodeError, RecursionError) as exc:
                        raise ProviderError(f"{name} invalid JSON") from exc
                    if not isinstance(payload, (dict, list)):
                        raise ProviderError(f"{name} invalid response shape")
                    return Response(
                        payload,
                        content,
                        url,
                        round((time.perf_counter() - start) * 1000),
                        response.headers.get("ratelimit-remaining"),
                    )
        except httpx.HTTPError as exc:
            if attempt == attempts - 1:
                raise ProviderError(f"{name} network request failed") from exc
            await asyncio.sleep(2**attempt)
    raise ProviderError(f"{name} request failed")
