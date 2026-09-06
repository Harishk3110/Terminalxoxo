"""Bounded read-only provider transport; errors never contain credentials or bodies."""

import asyncio
import json
import threading
import time
from dataclasses import dataclass

import httpx


class ProviderError(ValueError):
    def __init__(self, message, state="FAILED", status_code=None, retry_after=None):
        super().__init__(message)
        self.state = state
        self.status_code = status_code
        self.retry_after = retry_after


@dataclass
class Response:
    payload: dict | list
    content: bytes
    url: str
    latency_ms: int
    rate_remaining: str | None


_lock = threading.Lock()
_next_request: dict[str, float] = {}


async def pace(name, interval):
    # Reserve globally across adapter instances in this API process.
    with _lock:
        now = time.monotonic()
        scheduled = max(now, _next_request.get(name, now))
        _next_request[name] = scheduled + interval
    await asyncio.sleep(max(0, scheduled - now))


async def fetch(name, url, *, headers=None, params=None, body=None, interval=0.25, transport=None):
    headers = headers or {}
    for attempt in range(3):
        await pace(name, interval)
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(
                timeout=20, transport=transport, follow_redirects=False
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
                    if code >= 500 and attempt < 2:
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
                        payload = json.loads(content)
                    except (ValueError, UnicodeDecodeError) as exc:
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
            if attempt == 2:
                raise ProviderError(f"{name} network request failed") from exc
            await asyncio.sleep(2**attempt)
    raise ProviderError(f"{name} request failed")
