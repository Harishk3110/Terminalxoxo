from datetime import UTC, datetime

import httpx
import pytest
from app import models, provider_api
from app.config import Settings, get_settings
from app.database import get_session
from app.provider_data import adapters
from app.providers.http import ProviderError, fetch
from app.providers.market import JsonMarketProvider, PriceObservation
from app.providers.reference import OpenFigiProvider, SecProvider, cik_value, filing_rows
from app.quant_data import dataset_rows
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"facts": []},
        {"facts": {"us-gaap": []}},
        {"facts": {"us-gaap": {"Revenue": None}}},
        {"facts": {"us-gaap": {"Revenue": {"units": []}}}},
        {"facts": {"us-gaap": {"Revenue": {"units": {"USD": {}}}}}},
        {"facts": {"us-gaap": {"Revenue": {"units": {"USD": [None]}}}}},
        {"facts": {"us-gaap": {"Revenue": {"label": [], "units": {"USD": []}}}}},
    ],
)
def test_sec_facts_reject_malformed_nested_shapes(payload):
    with pytest.raises(ProviderError, match="SEC company facts"):
        provider_api.fact_rows(payload)


def test_sec_fact_cannot_override_its_taxonomy_concept_or_unit() -> None:
    observation = {"val": 100, "taxonomy": "other", "concept": "other", "unit": "other"}
    rows = provider_api.fact_rows(
        {"facts": {"us-gaap": {"Revenue": {"label": "Revenue", "units": {"USD": [observation]}}}}}
    )
    assert rows == [
        {"val": 100, "taxonomy": "us-gaap", "concept": "Revenue", "unit": "USD", "label": "Revenue"}
    ]


@pytest.mark.parametrize("latency", [None, "12", True, -1, 1.5, 0, 12])
@pytest.mark.anyio
async def test_fred_probe_requires_observed_latency(ledger_session, monkeypatch, latency):
    from app.provider_data import connection
    from app.provider_probe import probe
    from app.providers.fred import FredProvider

    settings = Settings(fred_enabled=True, fred_api_key="mock-fred-key")
    adapter = FredProvider(settings)
    row = connection(ledger_session, "fred", settings)

    async def metadata(*args):
        return {"_knk_latency_ms": latency, "seriess": []}

    monkeypatch.setattr(adapter, "series_metadata", metadata)
    outcome = await probe(ledger_session, row, "fred", adapter)
    valid = isinstance(latency, int) and not isinstance(latency, bool) and latency >= 0
    assert outcome["connection_state"] == ("CONNECTED" if valid else "FAILED")
    assert (row.last_success is not None) is valid
    assert (row.last_failure is not None) is not valid


@pytest.mark.parametrize("both", [False, True])
def test_provider_result_requires_exactly_one_observation(ledger_session, both):
    from app.provider_data import connection, record_result
    from app.providers.http import Response

    row = connection(ledger_session, "sec", Settings(sec_user_agent="KnK test@example.test"))
    ledger_session.commit()
    with pytest.raises(ValueError, match="exactly one"):
        record_result(
            ledger_session,
            row,
            response=Response({}, b"{}", "test", 1, None) if both else None,
            error=ProviderError("test failure") if both else None,
        )
    assert row.last_success is None and row.last_failure is None
    assert not ledger_session.new


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def no_test_pacing(monkeypatch):
    async def immediate(*args):
        pass

    monkeypatch.setattr("app.providers.http.pace", immediate)


def submissions():
    return {
        "cik": "320193",
        "name": "Apple",
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000001"],
                "filingDate": ["2026-01-05"],
                "form": ["10-K"],
                "primaryDocument": ["aapl-2025.htm"],
            },
            "files": [{"name": "CIK0000320193-submissions-001.json"}],
        },
    }


def price(**updates):
    return {
        "symbol": "AAA",
        "currency": "SGD",
        "timestamp": "2026-01-09T20:00:00Z",
        "close": "125.12345678",
        "data_state": "EOD",
        "adjustment_state": "UNADJUSTED",
        **updates,
    }


@pytest.mark.anyio
async def test_sec_contact_header_identity_and_document_validation():
    def handler(request):
        assert request.headers["User-Agent"] == "KnK test@example.test"
        assert request.url == "https://data.sec.gov/submissions/CIK0000320193.json"
        return httpx.Response(200, json=submissions())

    provider = SecProvider(
        Settings(SEC_USER_AGENT="KnK test@example.test"), httpx.MockTransport(handler)
    )
    response = await provider.read("320193")
    rows = filing_rows(response.payload)
    assert rows[0]["url"].startswith(
        "https://www.sec.gov/Archives/edgar/data/320193/000032019326000001/"
    )
    assert cik_value("320193") == "0000320193"
    bad = submissions()
    bad["filings"]["recent"]["primaryDocument"] = ["../../secrets"]
    with pytest.raises(ProviderError):
        filing_rows(bad)
    with pytest.raises(ValueError):
        cik_value("https://localhost")
    with pytest.raises(ProviderError, match="SEC_USER_AGENT"):
        await SecProvider(Settings()).read("320193")


@pytest.mark.anyio
async def test_rate_limit_and_redacted_failure():
    def handler(request):
        assert request.headers["X-OPENFIGI-APIKEY"] == "secret-not-logged"
        return httpx.Response(429, text="secret-not-logged", headers={"retry-after": "30"})

    provider = OpenFigiProvider(
        Settings(OPENFIGI_API_KEY="secret-not-logged"), httpx.MockTransport(handler)
    )
    with pytest.raises(ProviderError) as caught:
        await provider.mapping([{"idType": "TICKER", "idValue": "AAA"}])
    assert caught.value.state == "RATE_LIMITED"
    assert caught.value.retry_after == "30"
    assert "secret-not-logged" not in str(caught.value)
    with pytest.raises(ValueError):
        await OpenFigiProvider(Settings()).mapping([{"idType": "TICKER", "idValue": "AAA"}] * 11)


@pytest.mark.anyio
async def test_json_contract_auth_and_no_redirects():
    def handler(request):
        assert request.headers["Authorization"] == "Bearer server-secret"
        assert request.url.path == "/api/prices"
        assert request.url.params["symbol"] == "AAA"
        return httpx.Response(200, json={"rows": [price()]})

    provider = JsonMarketProvider(
        Settings(
            MARKET_DATA_BASE_URL="https://quotes.example.test/api",
            market_api_key="server-secret",
        ),
        transport=httpx.MockTransport(handler),
    )
    _, rows = await provider.read("AAA")
    assert rows[0]["close"] == "125.12345678"
    provider.transport = httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"location": "https://another.test"})
    )
    with pytest.raises(ProviderError, match="HTTP 302"):
        await provider.read("AAA")
    assert not JsonMarketProvider(Settings(MARKET_DATA_BASE_URL="http://example.test")).configured
    assert not JsonMarketProvider(
        Settings(MARKET_DATA_BASE_URL="https://user:secret@example.test")
    ).configured


@pytest.mark.parametrize(
    "updates",
    [
        {"timestamp": "2026-01-01"},
        {"timestamp": "2099-01-01T00:00:00Z"},
        {"close": "NaN"},
        {"high": "100"},
        {"low": "200"},
        {"data_state": "DEMO"},
        {"volume": "-1"},
    ],
)
def test_market_rows_reject_invalid_or_undisclosed_data(updates):
    with pytest.raises(ValueError):
        PriceObservation.model_validate(price(**updates))


@pytest.fixture
def provider_client(ledger_session, session_token, tmp_path, monkeypatch):
    settings = get_settings()
    for key, value in {
        "object_storage_local_dir": str(tmp_path),
        "sec_user_agent": "KnK test@example.test",
        "sec_enabled": True,
        "openfigi_enabled": True,
        "openfigi_api_key": "server-only-secret",
        "market_enabled": True,
        "market_base_url": "https://market.example.test",
        "options_enabled": False,
    }.items():
        monkeypatch.setattr(settings, key, value)

    def handler(request):
        if request.url.host == "data.sec.gov":
            return httpx.Response(200, json=submissions())
        if request.url.host == "api.openfigi.com":
            return httpx.Response(
                200,
                json=[
                    {
                        "data": [
                            {
                                "figi": "BBG000B9XRY4",
                                "ticker": "AAA",
                                "name": "Test AAA",
                                "exchCode": "US",
                                "securityType": "Common Stock",
                            },
                            {"figi": "BBG000BLNNH6", "ticker": "AAA", "exchCode": "LN"},
                        ]
                    }
                ],
            )
        return httpx.Response(200, json={"rows": [price()]})

    instances = adapters(settings)
    for item in instances.values():
        item.transport = httpx.MockTransport(handler)
    monkeypatch.setattr(provider_api, "adapters", lambda settings: instances)
    app = FastAPI()
    app.include_router(provider_api.router)
    app.dependency_overrides[get_session] = lambda: ledger_session
    with TestClient(app) as client:
        client.cookies.set("knk_session", session_token)
        yield client, instances


def test_provider_configuration_controls_and_no_secret_exposure(provider_client, ledger_session):
    client, _ = provider_client
    response = client.get("/api/v1/connections")
    assert response.status_code == 200
    assert "server-only-secret" not in response.text
    assert {row["key"] for row in response.json()["items"]} >= {
        "sec",
        "fred",
        "openfigi",
        "market",
        "options",
    }
    tested = client.post("/api/v1/connections/sec/test").json()
    assert tested["connection_state"] == "CONNECTED" and tested["last_success"]
    assert (
        client.post("/api/v1/connections/sec/control", json={"action": "REVOKE"}).json()[
            "connection_state"
        ]
        == "REVOKED"
    )
    assert client.post("/api/v1/connections/sec/test").status_code == 422
    assert client.post("/api/v1/connections/sec/import", json={"cik": "320193"}).status_code == 422
    assert (
        client.post("/api/v1/connections/sec/control", json={"action": "ENABLE"}).json()[
            "connection_state"
        ]
        == "NOT_TESTED"
    )
    assert ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.action == "PROVIDER_REVOKE")
    )
    client.cookies.clear()
    assert client.get("/api/v1/connections").status_code == 403


def test_sec_immutable_version_dedup_and_hash(provider_client, ledger_session):
    client, _ = provider_client
    one = client.post("/api/v1/connections/sec/import", json={"cik": "320193"}).json()
    assert one["state"] == "IMPORTED", one
    two = client.post("/api/v1/connections/sec/import", json={"cik": "320193"}).json()
    assert two["state"] == "UNCHANGED" and two["dataset_version_id"] == one["dataset_version_id"]
    rows = client.get("/api/v1/connections/sec/filings?cik=320193").json()["items"]
    assert len(rows) == 1 and rows[0]["form"] == "10-K"
    _, meta = dataset_rows(ledger_session, one["dataset_version_id"])
    assert meta["source"] == "SEC EDGAR"
    assert ledger_session.scalar(select(func.count()).select_from(models.PortfolioTransaction)) == 1


def test_figi_candidates_require_explicit_review_and_reject_conflict(
    provider_client, ledger_session
):
    client, _ = provider_client
    looked = client.post(
        "/api/v1/connections/openfigi/mapping",
        json={"jobs": [{"idType": "TICKER", "idValue": "AAA"}]},
    ).json()
    assert looked["state"] == "REVIEW_REQUIRED"
    assert ledger_session.get(models.Instrument, "AAA").figi is None
    approval = {
        "dataset_version_id": looked["dataset_version_id"],
        "job_index": 0,
        "figi": "BBG000B9XRY4",
        "instrument_id": "AAA",
    }
    assert client.post("/api/v1/connections/openfigi/accept", json=approval).status_code == 422
    approval["confirm"] = True
    assert (
        client.post("/api/v1/connections/openfigi/accept", json=approval).json()["state"]
        == "APPROVED"
    )
    assert (
        client.post(
            "/api/v1/connections/openfigi/accept", json={**approval, "instrument_id": "BBB"}
        ).status_code
        == 422
    )
    assert ledger_session.get(models.Instrument, "AAA").figi == approval["figi"]


def test_market_source_precedence_and_retry_does_not_duplicate(provider_client, ledger_session):
    from app.price_sources import MarketPriceResolver

    client, _ = provider_client
    result = client.post("/api/v1/connections/market/backfill", json={"symbol": "AAA"}).json()
    assert result["state"] == "IMPORTED", result
    retry = client.post("/api/v1/connections/market/backfill", json={"symbol": "AAA"}).json()
    assert retry["state"] == "UNCHANGED"
    observed = MarketPriceResolver(ledger_session, ["AAA"]).describe(
        "AAA", datetime(2026, 1, 10, tzinfo=UTC)
    )
    assert observed["source_category"] == "PROVIDER" and observed["data_state"] == "EOD"
    assert observed["value"] == "125.12345678"
    assert observed["dataset_version_id"] == result["dataset_version_id"]


def test_provider_failure_records_safe_health_and_no_partial_dataset(
    provider_client, ledger_session, monkeypatch
):
    client, providers = provider_client
    providers["market"].transport = httpx.MockTransport(
        lambda request: httpx.Response(429, text="server-only-secret")
    )
    response = client.post("/api/v1/connections/market/backfill", json={"symbol": "AAA"})
    assert response.json()["state"] == "RATE_LIMITED"
    assert "server-only-secret" not in response.text
    assert ledger_session.scalar(select(func.count()).select_from(models.DatasetVersion)) == 0
    states = client.get("/api/v1/connections").json()["items"]
    assert next(row for row in states if row["key"] == "market")["rate_limit"] == "RATE_LIMITED"


def test_fred_disable_applies_to_legacy_ingestion(provider_client, ledger_session):
    import asyncio

    from app.providers.fred import FredProvider
    from app.services import FredIngestionService

    client, _ = provider_client
    client.post("/api/v1/connections/fred/control", json={"action": "DISABLE"})
    provider = FredProvider(
        Settings(FRED_ENABLED=True, FRED_API_KEY="secret"),
        httpx.MockTransport(lambda request: pytest.fail("Disabled FRED must not request network")),
    )
    result = asyncio.run(
        FredIngestionService(ledger_session, provider).refresh_series("GDP", "test")
    )
    assert result["state"] == "DISABLED"


def test_storage_failure_rolls_back_import_but_records_failure(
    provider_client, ledger_session, monkeypatch
):
    from app.object_storage import ObjectStorage

    client, _ = provider_client

    def fail_write(*args, **kwargs):
        raise OSError("unavailable")

    monkeypatch.setattr(ObjectStorage, "put_bytes", fail_write)
    result = client.post("/api/v1/connections/sec/import", json={"cik": "320193"}).json()
    assert result["state"] == "FAILED"
    assert ledger_session.scalar(select(func.count()).select_from(models.DatasetVersion)) == 0
    assert ledger_session.scalar(select(func.count()).select_from(models.Dataset)) == 0
    assert (
        ledger_session.scalar(
            select(models.ProviderHealthSnapshot).where(
                models.ProviderHealthSnapshot.provider_name == "SEC EDGAR"
            )
        ).state
        == "FAILED"
    )


@pytest.mark.anyio
@pytest.mark.parametrize(
    "body",
    [
        b'{"value":NaN}',
        b'{"value":Infinity}',
        b'{"value":-Infinity}',
        b'{"value":1e400}',
        b'{"rows": [',
    ],
)
async def test_transport_rejects_malformed_or_nonfinite_json(body):
    with pytest.raises(ProviderError, match="invalid JSON"):
        await fetch(
            "fixture",
            "https://fixture.example.test",
            transport=httpx.MockTransport(lambda request: httpx.Response(200, content=body)),
        )


@pytest.mark.parametrize("payload", [None, [], {"filings": []}, {"filings": {"recent": None}}])
def test_sec_rejects_malformed_containers(payload):
    with pytest.raises(ProviderError):
        filing_rows(payload)


@pytest.mark.parametrize("key", ["accessionNumber", "filingDate", "form", "primaryDocument"])
def test_sec_rejects_nonstring_column_cells(key):
    payload = submissions()
    payload["filings"]["recent"][key] = [123]
    with pytest.raises(ProviderError, match="must contain strings"):
        filing_rows(payload)
