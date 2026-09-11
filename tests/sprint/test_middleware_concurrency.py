"""Synchronous database waits must not block ASGI response and session cleanup."""

import asyncio
import threading
from collections.abc import Awaitable, Callable

import pytest
from app import main, terminal_api
from fastapi import Request, Response
from sqlalchemy.orm import Session


@pytest.mark.parametrize("phase", ["startup", "authentication"])
def test_database_wait_leaves_the_event_loop_available(
    monkeypatch: pytest.MonkeyPatch, phase: str
) -> None:
    entered, released = threading.Event(), threading.Event()
    observed: list[bool] = []
    called_threads: list[int] = []
    loop_thread = threading.get_ident()

    def blocked_database_call() -> None:
        called_threads.append(threading.get_ident())
        entered.set()
        observed.append(released.wait(2))

    def authenticate(request: Request, session: Session) -> dict[str, bool]:
        blocked_database_call()
        return {"authenticated": True}

    monkeypatch.setattr(main, "ensure_database_ready", lambda: None)
    monkeypatch.setattr(main, "SessionLocal", Session)
    monkeypatch.setattr(terminal_api, "auth_session", authenticate)
    if phase == "startup":
        monkeypatch.setattr(main, "ensure_database_ready", blocked_database_call)
    path = "/health/live" if phase == "startup" else "/api/v1/private-test"
    request = Request({"type": "http", "method": "GET", "path": path, "headers": []})

    async def next_response(request: Request) -> Response:
        return Response("available")

    async def run() -> Response:
        async def cleanup_other_request() -> None:
            assert await asyncio.to_thread(entered.wait, 3)
            released.set()

        cleanup = asyncio.create_task(cleanup_other_request())
        try:
            return await main.request_middleware(request, next_response)
        finally:
            await cleanup

    response = asyncio.run(run())
    assert response.status_code == 200
    assert observed == [True]
    assert called_threads and loop_thread not in called_threads


@pytest.mark.parametrize(
    "method,path,headers,authenticated,status,auth_calls,route_calls",
    [
        ("GET", "/api/v1/private-test", [], False, 401, 1, 0),
        ("GET", "/api/v1/private-test", [], True, 200, 1, 1),
        ("POST", "/api/v1/private-test", [(b"sec-fetch-site", b"cross-site")], True, 403, 0, 0),
        ("POST", "/api/v1/auth/login", [], False, 200, 0, 1),
        ("OPTIONS", "/api/v1/private-test", [], False, 200, 0, 1),
    ],
)
def test_request_access_and_security_headers_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
    method: str,
    path: str,
    headers: list[tuple[bytes, bytes]],
    authenticated: bool,
    status: int,
    auth_calls: int,
    route_calls: int,
) -> None:
    counts = {"auth": 0, "route": 0}

    def authenticate(request: Request, session: Session) -> dict[str, bool]:
        counts["auth"] += 1
        return {"authenticated": authenticated}

    async def next_response(request: Request) -> Response:
        counts["route"] += 1
        return Response("available")

    monkeypatch.setattr(main, "ensure_database_ready", lambda: None)
    monkeypatch.setattr(main, "SessionLocal", Session)
    monkeypatch.setattr(terminal_api, "auth_session", authenticate)
    request = Request({"type": "http", "method": method, "path": path, "headers": headers})
    call_next: Callable[[Request], Awaitable[Response]] = next_response
    response = asyncio.run(main.request_middleware(request, call_next))
    assert response.status_code == status
    assert counts == {"auth": auth_calls, "route": route_calls}
    assert response.headers["Cache-Control"] == "no-store"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Robots-Tag"] == "noindex, nofollow"
    assert response.headers["X-Frame-Options"] == "DENY"
