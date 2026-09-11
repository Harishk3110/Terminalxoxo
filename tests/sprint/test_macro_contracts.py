"""Macro responses preserve observed provenance, precision and bounded history."""

from collections.abc import Iterator
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from app import models
from app.database import get_session
from app.main import macro_observations
from app.services import MacroService
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


@pytest.fixture
def macro_session(ledger_session: Session) -> Session:
    ledger_session.add(
        models.MacroSeries(
            series_id="TEST_RATE",
            title="Recorded test rate",
            units="Percent",
            frequency="Daily",
            provider="FRED",
            quality="EOD DATA",
        )
    )
    ledger_session.flush()
    for day, value in ((27, Decimal("1.12345678")), (28, Decimal("0"))):
        ledger_session.add(
            models.MacroObservation(
                series_id="TEST_RATE",
                observation_date=date(2026, 8, day),
                value=value,
                provider="Imported observation",
                quality="FILE IMPORT",
                ingestion_timestamp=datetime(2026, 9, 12, tzinfo=UTC),
            )
        )
    ledger_session.flush()
    return ledger_session


def test_dashboard_source_belongs_to_observation_not_series_metadata(
    macro_session: Session,
) -> None:
    item = MacroService(macro_session).dashboard()["items"][0]
    assert item["source"] == "Imported observation"
    assert item["quality"] == "FILE IMPORT"
    assert item["latest_value"] == "0E-8"
    assert item["previous_value"] == "1.12345678"
    assert item["change"] == "-1.12345678"
    assert item["latest_observation_date"] == "2026-08-28"
    assert str(item["ingestion_timestamp"]).startswith("2026-09-12T00:00:00")


def test_missing_observation_does_not_inherit_a_value_or_timestamp(ledger_session: Session) -> None:
    ledger_session.add(
        models.MacroSeries(
            series_id="EMPTY",
            title="Empty",
            units="Percent",
            frequency="Daily",
            provider="FRED",
            quality="UNAVAILABLE",
        )
    )
    ledger_session.flush()
    item = MacroService(ledger_session).dashboard()["items"][0]
    assert item["source"] == "FRED"
    assert item["latest_value"] is None
    assert item["latest_observation_date"] is None
    assert item["previous_value"] is None
    assert item["change"] is None
    assert item["ingestion_timestamp"] is None
    assert item["revision_state"] == "UNAVAILABLE"


def test_history_preserves_nulls_decimal_precision_and_chronology(macro_session: Session) -> None:
    macro_session.add(
        models.MacroObservation(
            series_id="TEST_RATE",
            observation_date=date(2026, 8, 29),
            value=None,
            provider="FRED",
            quality="UNAVAILABLE",
            realtime_start=date(2026, 8, 30),
            realtime_end=date(2026, 9, 1),
        )
    )
    macro_session.flush()
    history = MacroService(macro_session).observations("TEST_RATE", 2)
    assert history["series"]["provider"] == "FRED"
    assert history["observations"] == [
        {
            "date": "2026-08-28",
            "value": "0E-8",
            "provider": "Imported observation",
            "quality": "FILE IMPORT",
            "realtime_start": None,
            "realtime_end": None,
        },
        {
            "date": "2026-08-29",
            "value": None,
            "provider": "FRED",
            "quality": "UNAVAILABLE",
            "realtime_start": "2026-08-30",
            "realtime_end": "2026-09-01",
        },
    ]
    assert MacroService(macro_session).series("recorded")[0]["series_id"] == "TEST_RATE"
    assert MacroService(macro_session).series("no-such-series") == []


@pytest.fixture
def macro_client(macro_session: Session) -> Iterator[TestClient]:
    application = FastAPI()
    application.add_api_route("/macro/{series_id}", macro_observations)

    def session_override() -> Iterator[Session]:
        yield macro_session

    application.dependency_overrides[get_session] = session_override
    with TestClient(application) as client:
        yield client


@pytest.mark.parametrize("limit", ["-1", "0", "10001", "2.5", "invalid"])
def test_history_http_rejects_invalid_limits(macro_client: TestClient, limit: str) -> None:
    response = macro_client.get(f"/macro/TEST_RATE?limit={limit}")
    assert response.status_code == 422


@pytest.mark.parametrize("limit", [1, 1000, 10000])
def test_history_http_accepts_supported_limits(macro_client: TestClient, limit: int) -> None:
    response = macro_client.get(f"/macro/TEST_RATE?limit={limit}")
    assert response.status_code == 200
    assert len(response.json()["observations"]) == min(limit, 2)


def test_unknown_series_remains_not_found(macro_client: TestClient) -> None:
    response = macro_client.get("/macro/UNKNOWN")
    assert response.status_code == 404
    assert response.json()["detail"] == "Macro series unavailable"


@pytest.mark.parametrize("limit", [-1, 0, 10001])
def test_service_also_bounds_history_before_querying(macro_session: Session, limit: int) -> None:
    with pytest.raises(ValueError, match="Observation limit must be between"):
        MacroService(macro_session).observations("TEST_RATE", limit)
