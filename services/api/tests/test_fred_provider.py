import httpx
import pytest
from app.config import Settings
from app.providers.fred import FredObservationsResponse, FredProvider


@pytest.mark.anyio
async def test_fred_provider_parses_mocked_metadata_and_observations():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/series"):
            return httpx.Response(
                200,
                json={
                    "seriess": [
                        {
                            "id": "FEDFUNDS",
                            "title": "Effective Federal Funds Rate",
                            "frequency": "Monthly",
                            "units": "Percent",
                        }
                    ]
                },
            )
        if request.url.path.endswith("/series/observations"):
            return httpx.Response(
                200,
                json={
                    "observations": [
                        {
                            "realtime_start": "2026-01-01",
                            "realtime_end": "2026-01-01",
                            "date": "2026-01-01",
                            "value": "4.25",
                        },
                        {"date": "2026-02-01", "value": "."},
                    ]
                },
            )
        if request.url.path.endswith("/series/vintagedates"):
            return httpx.Response(200, json={"vintage_dates": ["2026-01-01"]})
        return httpx.Response(404)

    provider = FredProvider(
        Settings(
            FRED_ENABLED=True,
            fred_api_key="mock-fred-key",
            DATABASE_URL="sqlite:///:memory:",
        ),
        transport=httpx.MockTransport(handler),
    )
    metadata = await provider.series_metadata("FEDFUNDS", "test-correlation")
    observations = await provider.observations("FEDFUNDS", "test-correlation")
    parsed = FredObservationsResponse.model_validate(observations)
    assert metadata["seriess"][0]["id"] == "FEDFUNDS"
    assert parsed.observations[0].decimal_value is not None
    assert parsed.observations[1].decimal_value is None
