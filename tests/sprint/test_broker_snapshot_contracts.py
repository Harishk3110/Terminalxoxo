"""Stored paper snapshots remain validated financial inputs, not trusted JSON."""

from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from app import broker_api, models
from app.portfolio_operations import PortfolioLedgerService
from fastapi import HTTPException
from pydantic import JsonValue, TypeAdapter
from sqlalchemy.orm import Session
from starlette.requests import Request

JSON_OBJECT = TypeAdapter(dict[str, JsonValue])


def recorded_fill() -> dict[str, JsonValue]:
    return {
        "execution_id": "recorded-fill",
        "symbol": "AAA",
        "currency": "SGD",
        "side": "BOT",
        "contract_type": "STK",
        "quantity": "1.2500",
        "price": "120.00",
        "commission": "0.00",
        "commission_currency": "SGD",
        "time": "2026-01-07T00:30:00+08:00",
    }


def stored_snapshot(
    session: Session, payload: dict[str, JsonValue]
) -> models.BrokerAccountSnapshot:
    row = models.BrokerAccountSnapshot(
        portfolio_id="book",
        external_reference="contract-snapshot",
        as_of=datetime.now(UTC),
        source="IBKR PAPER",
        connected=True,
        nav=Decimal("700"),
        currency="SGD",
        payload=payload,
    )
    session.add(row)
    session.flush()
    return row


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([], "0"),
        ([Decimal(0)], "0"),
        ([Decimal("1.25"), Decimal("-1.25")], "0.00"),
        ([None], None),
        ([Decimal(0), None], None),
    ],
)
def test_total_distinguishes_missing_from_zero(
    values: Sequence[Decimal | None], expected: str | None
) -> None:
    assert broker_api.complete_total(values) == expected


@pytest.mark.parametrize("agent_id", [None, 1, [], {"id": "unknown"}, "unknown"])
def test_unusable_agent_identity_cannot_report_connected(
    ledger_session: Session, agent_id: JsonValue
) -> None:
    row = stored_snapshot(ledger_session, {"agent_id": agent_id})
    selected, connected = broker_api.current_snapshot(ledger_session, "book")
    assert selected is row
    assert connected is False


def test_snapshot_without_main_profile_is_not_connected(ledger_session: Session) -> None:
    assert broker_api.snapshot(ledger_session) == {"state": "NOT CONNECTED", "snapshot": None}


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fills", None),
        ("fills", 1),
        ("fills", ["bad-record"]),
        ("fills", [{"execution_id": "recorded-fill"}]),
        ("account_fingerprint", None),
        ("account_fingerprint", {}),
        ("account_fingerprint", "not-a-fingerprint"),
    ],
)
def test_malformed_persisted_fills_fail_before_ledger_write(
    ledger_session: Session, monkeypatch: pytest.MonkeyPatch, field: str, value: JsonValue
) -> None:
    data: dict[str, JsonValue] = {"account_fingerprint": "a" * 64, "fills": [recorded_fill()]}
    data[field] = value
    row = stored_snapshot(ledger_session, data)
    monkeypatch.setattr(broker_api, "identity", lambda *_: "authenticated-reviewer")

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Malformed broker input reached the ledger")

    monkeypatch.setattr(PortfolioLedgerService, "add", forbidden)
    with pytest.raises(HTTPException) as error:
        broker_api.approve_fill(
            broker_api.ApproveFillRequest(
                snapshot_id=row.id,
                execution_id="recorded-fill",
                transaction_type="BUY",
                fx_rate_to_base="1",
                rationale="Reviewed recorded fill",
            ),
            Request({"type": "http", "headers": []}),
            ledger_session,
        )
    assert error.value.status_code == 422
    assert error.value.detail == "Recorded broker fill data is invalid; reconciliation required"


@pytest.mark.parametrize(
    ("changes", "transaction_type", "status"),
    [
        ({"side": "UNKNOWN"}, "SELL", 422),
        ({"side": "BOT"}, "SELL", 422),
        ({"contract_type": "OPT"}, "BUY", 422),
        ({"commission": None}, "BUY", 422),
        ({"commission_currency": "USD"}, "BUY", 422),
        ({"execution_id": "another-fill"}, "BUY", 404),
    ],
)
def test_recorded_fill_guards_precede_ledger_write(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    changes: dict[str, JsonValue],
    transaction_type: str,
    status: int,
) -> None:
    row = stored_snapshot(
        ledger_session,
        {
            "account_fingerprint": "a" * 64,
            "fills": [{**recorded_fill(), **changes}],
        },
    )
    monkeypatch.setattr(broker_api, "identity", lambda *_: "authenticated-reviewer")

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("Invalid broker fill reached the ledger")

    monkeypatch.setattr(PortfolioLedgerService, "add", forbidden)
    with pytest.raises(HTTPException) as error:
        broker_api.approve_fill(
            broker_api.ApproveFillRequest(
                snapshot_id=row.id,
                execution_id="recorded-fill",
                transaction_type=transaction_type,
                fx_rate_to_base="1",
                rationale="Reviewed recorded fill",
            ),
            Request({"type": "http", "headers": []}),
            ledger_session,
        )
    assert error.value.status_code == status


def test_valid_fill_preserves_recorded_decimal_strings_date_and_dedup_identity(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    row = stored_snapshot(
        ledger_session,
        {
            "account_fingerprint": "a" * 64,
            "fills": [recorded_fill()],
        },
    )
    monkeypatch.setattr(broker_api, "identity", lambda *_: "authenticated-reviewer")
    observed: list[dict[str, JsonValue]] = []

    def add(
        _service: object, payload: dict[str, object], portfolio_id: str, *, source: str, actor: str
    ) -> dict[str, JsonValue]:
        assert portfolio_id == "book" and source == "IBKR PAPER"
        assert actor == "authenticated-reviewer"
        observed.append(JSON_OBJECT.validate_python(payload, strict=True))
        return {"id": "transaction", "trade_event_id": "review-event"}

    monkeypatch.setattr(PortfolioLedgerService, "add", add)
    result = broker_api.approve_fill(
        broker_api.ApproveFillRequest(
            snapshot_id=row.id,
            execution_id="recorded-fill",
            transaction_type="BUY",
            fx_rate_to_base="1",
            rationale="Reviewed recorded fill",
        ),
        Request({"type": "http", "headers": []}),
        ledger_session,
    )
    assert result == {"id": "transaction", "trade_event_id": "review-event"}
    assert observed == [
        {
            "transaction_type": "BUY",
            "trade_date": "2026-01-07",
            "symbol": "AAA",
            "quantity": "1.2500",
            "price": "120.00",
            "currency": "SGD",
            "commission": "0.00",
            "fx_rate_to_base": "1",
            "external_reference": "a" * 64 + ":recorded-fill",
            "notes": "Reviewed recorded fill",
            "metadata": {"broker_snapshot_id": row.id, "execution_id": "recorded-fill"},
        }
    ]


@pytest.mark.parametrize(
    ("section", "field", "invalid"),
    [
        ("fx", "SGD", "2"),
        ("fx", "USD", "0"),
        ("fx", "USD", "-1"),
        ("fx", "USD", "NaN"),
        ("fx", "USD", "Infinity"),
        ("cash", "amount", "NaN"),
        ("cash", "amount", "Infinity"),
        ("positions", "quantity", "NaN"),
        ("positions", "market_price", "0"),
        ("positions", "market_price", "-120"),
        ("positions", "market_price", "NaN"),
        ("positions", "multiplier", "0"),
        ("positions", "multiplier", "-1"),
    ],
)
def test_invalid_persisted_values_never_produce_broker_financials(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    section: str,
    field: str,
    invalid: str,
) -> None:
    cash: dict[str, JsonValue] = {"currency": "USD", "amount": "100"}
    position: dict[str, JsonValue] = {
        "symbol": "AAA",
        "currency": "SGD",
        "quantity": "5",
        "market_price": "120",
        "multiplier": "1",
        "average_cost": "100",
    }
    fx: dict[str, JsonValue] = {"USD": "1.25"}
    {"cash": cash, "positions": position, "fx": fx}[section][field] = invalid
    row = stored_snapshot(ledger_session, {"cash": [cash], "positions": [position], "fx": fx})
    monkeypatch.setattr(broker_api, "current_snapshot", lambda *_: (row, True))
    with pytest.raises(ValueError):
        broker_api.account_view(
            ledger_session,
            {
                "portfolio": {"id": "book", "nav": "10000"},
                "performance": {},
                "risk": {},
            },
        )
