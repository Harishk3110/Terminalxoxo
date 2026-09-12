from collections.abc import Iterator
from copy import deepcopy
from datetime import UTC, datetime

import pytest
from app import models
from app.database import get_session
from app.equity_api import financial_report, router
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import JsonValue
from sqlalchemy import func, select
from sqlalchemy.orm import Session


@pytest.fixture
def equity_client(
    ledger_session: Session, session_token: str, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    for key in ("AAA", "BBB"):
        ledger_session.add(
            models.FundamentalSnapshot(
                instrument_id=key,
                source="TEST FILE",
                quality="FILE IMPORT",
                as_of=datetime(2025, 12, 31, tzinfo=UTC),
                statements={
                    "items": [
                        {
                            "year": "2025",
                            "revenue": 100,
                            "debt": 20,
                            "cash": 10,
                            "shares": 10,
                            "net_income": 15,
                        }
                    ]
                },
            )
        )
    ledger_session.commit()
    monkeypatch.setattr(
        "app.equity_api.quotes",
        lambda _s: [
            {"id": key, "symbol": key, "price": 10, "quality": "FILE IMPORT", "source": "TEST"}
            for key in ("AAA", "BBB")
        ],
    )
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        yield client


def test_saved_dcf_pins_original_statements_and_audit(
    equity_client: TestClient, ledger_session: Session
) -> None:
    response = equity_client.post(
        "/api/v1/equity/dcf",
        json={
            "symbol": "AAA",
            "scenarios": [{"name": "BASE"}, {"name": "BULL", "revenue_growth": [0.12] * 5}],
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    saved = ledger_session.get(models.AnalysisRun, data["id"])
    assert saved is not None
    original = deepcopy(saved.result)
    snapshot = ledger_session.scalar(
        select(models.FundamentalSnapshot).where(models.FundamentalSnapshot.instrument_id == "AAA")
    )
    assert snapshot is not None
    snapshot.statements = {"items": []}
    ledger_session.commit()
    assert saved.result == original and len(data["input_hash"]) == 64
    assert ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.action == "DCF_CREATED")
    )
    assert data["scenarios"][1]["name"] == "BULL"


def test_thesis_versions_preserve_history_and_require_valid_links(
    equity_client: TestClient, ledger_session: Session
) -> None:
    payload = {"symbol": "AAA", "title": "Test thesis", "one_sentence": "A falsifiable thesis"}
    first = equity_client.post("/api/v1/equity/theses", json=payload)
    assert first.status_code == 201, first.text
    second = equity_client.post(
        "/api/v1/equity/theses",
        json={
            **payload,
            "parent_id": first.json()["id"],
            "state": "REVIEW",
            "risks": "Margin contraction",
        },
    )
    assert second.status_code == 201
    assert second.json()["version"] == 2
    first_reference = ledger_session.get(models.InvestmentThesis, first.json()["id"])
    second_reference = ledger_session.get(models.InvestmentThesis, second.json()["id"])
    first_analysis = ledger_session.get(models.AnalysisRun, first.json()["id"])
    assert first_reference is not None and second_reference is not None
    assert first_analysis is not None and first_analysis.result is not None
    assert first_reference.summary == payload["one_sentence"]
    assert second_reference.thesis_state == "REVIEW"
    assert first_analysis.result["state"] == "DRAFT"
    assert len(equity_client.get("/api/v1/equity/theses?symbol=AAA").json()["items"]) == 2
    assert (
        equity_client.post(
            "/api/v1/equity/theses",
            json={**payload, "parent_id": first.json()["id"], "symbol": "BBB"},
        ).status_code
        == 422
    )
    assert (
        equity_client.post(
            "/api/v1/equity/theses", json={**payload, "bull_probability": 0.9}
        ).status_code
        == 422
    )
    assert (
        equity_client.post(
            "/api/v1/equity/theses", json={**payload, "attachment_ids": ["missing"]}
        ).status_code
        == 422
    )


def test_financials_peer_stats_and_auth(equity_client: TestClient) -> None:
    report = equity_client.get("/api/v1/equity/AAA/financials").json()
    assert report["ratios"][0]["pe"] == pytest.approx(100 / 15)
    assert (
        equity_client.get("/api/v1/equity/AAA/financials?frequency=TTM").json()["state"]
        == "INSUFFICIENT_DATA"
    )
    peers = equity_client.post(
        "/api/v1/equity/comparables", json={"symbol": "AAA", "peers": ["AAA", "BBB", "BBB"]}
    )
    assert peers.status_code == 201, peers.text
    assert len(peers.json()["items"]) == 2
    assert peers.json()["statistics"][0]["count"] == 1
    equity_client.cookies.clear()
    assert equity_client.get("/api/v1/equity/AAA/financials").status_code == 403


def test_snapshot_does_not_invent_bid_ask_or_vwap(equity_client: TestClient) -> None:
    response = equity_client.get("/api/v1/equity/AAA/snapshot")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["quote"]["last"] == 120
    assert data["quote"]["bid"] is None and data["quote"]["ask"] is None
    assert data["quote"]["vwap"] is None and data["quote"]["spread"] is None
    assert data["provenance"]["source"] == "TEST"


def test_snapshot_keeps_missing_legacy_history_ranges_unavailable(
    equity_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "app.equity_api.history",
        lambda _session, _key, _limit: {
            "items": [{"date": datetime.now(UTC).date().isoformat(), "close": 120.0}]
        },
    )
    response = equity_client.get("/api/v1/equity/AAA/snapshot")
    assert response.status_code == 200, response.text
    assert response.json()["fifty_two_week_low"] is None
    assert response.json()["fifty_two_week_high"] is None


def financial_evidence() -> dict[str, JsonValue]:
    return {
        "symbol": "AAA",
        "source": "TEST FILE",
        "quality": "FILE IMPORT",
        "unit": "USD millions",
        "as_of": "2025-12-31",
        "items": [{"year": "2025", "revenue": 100, "net_income": 15, "shares": 10}],
    }


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("symbol", None),
        ("symbol", "BBB"),
        ("source", None),
        ("quality", []),
        ("as_of", 2025),
        ("unit", {}),
        ("warnings", None),
        ("warnings", [1]),
        ("lineage", {}),
        ("lineage", [1]),
        ("extension", {"nested": float("nan")}),
    ],
)
def test_financial_receipts_validate_before_calculation(
    equity_client: TestClient,
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: JsonValue,
) -> None:
    data = {**financial_evidence(), field: value}
    monkeypatch.setattr("app.equity_api.fundamentals", lambda _session, _key: data)
    called = False

    def reject_calculation(*args: object, **kwargs: object) -> dict[str, JsonValue]:
        nonlocal called
        called = True
        raise ValueError("Invalid source reached ratio calculation")

    monkeypatch.setattr("app.equity_api.ratios", reject_calculation)
    with pytest.raises(ValueError):
        financial_report(ledger_session, "AAA", quote={"price": 10})
    assert not called, "Invalid financial receipt reached the calculator"


@pytest.mark.parametrize(
    "quote",
    [
        {"price": True},
        {"price": "10"},
        {"price": float("nan")},
        {"price": []},
        {"price": 10, "as_of": 2025},
        {"price": 10, "id": "BBB"},
        {"price": 10, "symbol": "BBB"},
    ],
)
def test_financial_quote_validates_before_calculation(
    equity_client: TestClient,
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    quote: dict[str, object],
) -> None:
    called = False

    def reject_calculation(*args: object, **kwargs: object) -> dict[str, JsonValue]:
        nonlocal called
        called = True
        raise ValueError("Invalid quote reached ratio calculation")

    monkeypatch.setattr("app.equity_api.ratios", reject_calculation)
    with pytest.raises(ValueError):
        financial_report(ledger_session, "AAA", quote=quote)
    assert not called, "Invalid quote reached the calculator"


@pytest.mark.parametrize("quote", [{}, {"price": None}, {"price": 0}, {"price": 10}])
def test_financial_report_preserves_legacy_metadata_and_missing_prices(
    equity_client: TestClient,
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    quote: dict[str, object],
) -> None:
    data: dict[str, JsonValue] = {
        **financial_evidence(),
        "warnings": ["ORIGINAL SOURCE WARNING"],
        "lineage": [{"version_id": "v1", "revision": 0}],
        "extension": {"literal": "NaN", "zero": 0, "flag": False},
    }
    quote = {**quote, "vendor_metadata": {"version": 0, "approved": False}}
    original = deepcopy((data, quote))
    monkeypatch.setattr("app.equity_api.fundamentals", lambda _session, _key: data)
    report = financial_report(ledger_session, "AAA", quote=quote)
    assert report.get("extension") == data["extension"]
    assert report["lineage"] == data["lineage"]
    assert report["quote"] == quote
    assert list(report["quote"]) == list(quote)
    assert report["warnings"][0] == "ORIGINAL SOURCE WARNING"
    assert report["ratios"][0]["revenue"] == 100
    assert (data, quote) == original


def test_financial_http_response_keeps_source_extensions(
    equity_client: TestClient, ledger_session: Session
) -> None:
    snapshot = ledger_session.scalar(
        select(models.FundamentalSnapshot).where(models.FundamentalSnapshot.instrument_id == "AAA")
    )
    assert snapshot is not None
    extension: dict[str, JsonValue] = {"revision": 0, "verified": False, "literal": "NaN"}
    snapshot.statements = {**snapshot.statements, "extension": extension}
    ledger_session.commit()
    response = equity_client.get("/api/v1/equity/AAA/financials")
    assert response.status_code == 200, response.text
    assert response.json()["extension"] == extension
    schema = equity_client.get("/openapi.json").json()
    contract = schema["components"]["schemas"]["FinancialReport"]
    assert {"symbol", "items", "quote", "ratios", "warnings"} <= set(contract["required"])


@pytest.mark.parametrize(
    "invalid", [{"source": None}, {"extension": {"value": float("nan")}}, {"warnings": [1]}]
)
def test_financial_http_rejects_invalid_receipts_before_serialization(
    equity_client: TestClient, ledger_session: Session, invalid: dict[str, JsonValue]
) -> None:
    snapshot = ledger_session.scalar(
        select(models.FundamentalSnapshot).where(models.FundamentalSnapshot.instrument_id == "AAA")
    )
    assert snapshot is not None
    snapshot.statements = {**snapshot.statements, **invalid}
    ledger_session.commit()
    response = equity_client.get("/api/v1/equity/AAA/financials")
    assert response.status_code == 422, response.text


def test_financial_report_quote_order_is_preserved_in_exported_rows(
    equity_client: TestClient, ledger_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.report_contracts import ReportRequest, section
    from app.report_sources import capture

    quote: dict[str, JsonValue] = {
        "id": "AAA",
        "symbol": "AAA",
        "name": "Fixture security",
        "currency": "SGD",
        "price": 10,
        "source": "FIXTURE",
        "as_of": "2025-12-31",
    }
    monkeypatch.setattr("app.equity_api.quotes", lambda _session: [quote])
    report = financial_report(ledger_session, "AAA")
    assert list(report["quote"]) == list(quote)
    captured = capture(ledger_session, ReportRequest(kind="equity", format="xlsx", symbol="AAA"))
    actual = next(item for item in captured.sections if item.title == "Quote")
    assert actual == section("Quote", quote)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("result", None),
        ("status", "FAILED"),
        ("version", None),
        ("version", 0),
        ("version", -1),
        ("version", True),
        ("version", 1.5),
        ("version", "2"),
        ("version", []),
        ("version", {}),
        ("instrument_id", []),
    ],
)
def test_invalid_thesis_parent_rejects_before_saving_a_revision(
    equity_client: TestClient,
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    field: str,
    value: JsonValue,
) -> None:
    payload = {"symbol": "AAA", "title": "Parent", "one_sentence": "Original hypothesis"}
    created = equity_client.post("/api/v1/equity/theses", json=payload)
    assert created.status_code == 201, created.text
    row = ledger_session.get(models.AnalysisRun, created.json()["id"])
    assert row is not None and row.result is not None
    if field == "result":
        row.result = None
    elif field == "status":
        assert isinstance(value, str)
        row.status = value
    else:
        row.result = {**row.result, field: value}
    ledger_session.commit()
    original = deepcopy(row.result)
    audit_count = ledger_session.scalar(select(func.count(models.AuditLog.id)))
    writer_called = False

    def no_revision(*args: object, **kwargs: object) -> dict[str, JsonValue]:
        nonlocal writer_called
        writer_called = True
        raise ValueError("Invalid parent reached the analysis writer")

    monkeypatch.setattr("app.equity_api.save_analysis", no_revision)
    response = equity_client.post("/api/v1/equity/theses", json={**payload, "parent_id": row.id})
    assert response.status_code == 422, response.text
    assert not writer_called, "Invalid parent reached the analysis writer"
    assert ledger_session.scalar(select(func.count(models.AnalysisRun.id))) == 1
    assert ledger_session.scalar(select(func.count(models.InvestmentThesis.id))) == 1
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == audit_count
    assert row.result == original


@pytest.mark.parametrize("result", [None, {}, {"instrument_id": []}])
def test_invalid_dcf_link_cannot_create_a_thesis(
    equity_client: TestClient, ledger_session: Session, result: dict[str, JsonValue] | None
) -> None:
    run = models.AnalysisRun(
        kind="dcf",
        name="Invalid saved valuation",
        status="SUCCEEDED",
        parameters={},
        result=result,
        history=[],
    )
    ledger_session.add(run)
    ledger_session.commit()
    response = equity_client.post(
        "/api/v1/equity/theses",
        json={
            "symbol": "AAA",
            "title": "Linked thesis",
            "one_sentence": "Test",
            "dcf_run_id": run.id,
        },
    )
    assert response.status_code == 422, response.text
    assert ledger_session.scalar(select(func.count(models.AnalysisRun.id))) == 1
    assert ledger_session.scalar(select(func.count(models.InvestmentThesis.id))) == 0
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == 0


@pytest.mark.parametrize(
    "result", [None, {"symbol": []}, {"symbol": None}, {"symbol": "AAA", "id": "forged"}]
)
def test_thesis_list_rejects_malformed_saved_evidence(
    equity_client: TestClient, ledger_session: Session, result: dict[str, JsonValue] | None
) -> None:
    run = models.AnalysisRun(
        kind="thesis",
        name="Invalid saved thesis",
        status="SUCCEEDED",
        parameters={},
        result=result,
        history=[],
    )
    ledger_session.add(run)
    ledger_session.commit()
    response = equity_client.get("/api/v1/equity/theses?symbol=AAA")
    assert response.status_code == 422, response.text
    assert ledger_session.scalar(select(func.count(models.AnalysisRun.id))) == 1
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == 0


def test_legacy_parent_version_and_independent_branches_are_preserved(
    equity_client: TestClient, ledger_session: Session
) -> None:
    payload = {"symbol": "AAA", "title": "Legacy parent", "one_sentence": "Test"}
    first = equity_client.post("/api/v1/equity/theses", json=payload)
    assert first.status_code == 201, first.text
    row = ledger_session.get(models.AnalysisRun, first.json()["id"])
    assert row is not None and row.result is not None
    legacy = dict(row.result)
    del legacy["version"]
    row.result = legacy
    ledger_session.commit()
    branches = [
        equity_client.post("/api/v1/equity/theses", json={**payload, "parent_id": row.id})
        for _ in range(2)
    ]
    assert all(branch.status_code == 201 for branch in branches)
    assert branches[0].json()["id"] != branches[1].json()["id"]
    assert all(branch.json()["version"] == 2 for branch in branches)
    assert row.result == legacy
    assert ledger_session.scalar(select(func.count(models.InvestmentThesis.id))) == 3
