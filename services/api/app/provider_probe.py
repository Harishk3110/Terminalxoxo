from sqlalchemy.orm import Session

from . import models
from .provider_data import ProviderAdapter, ProviderPayload, provider_payload, record_result
from .providers.fred import FredProvider
from .providers.http import ProviderError, Response


async def probe(
    session: Session,
    row: models.ProviderConnection,
    key: str,
    adapter: ProviderAdapter,
    actor: str | None = None,
    correlation_id: str = "provider-test",
) -> ProviderPayload:
    if not row.enabled or not row.configured or row.connection_state == "REVOKED":
        raise ValueError("Provider is disabled, revoked or not configured")
    try:
        if isinstance(adapter, FredProvider):
            payload = await adapter.series_metadata("GDP", correlation_id)
            latency = payload.get("_knk_latency_ms")
            if isinstance(latency, bool) or not isinstance(latency, int) or latency < 0:
                raise ProviderError("Provider response lacks a valid observed latency")
            response = Response(payload, b"", "", latency, None)
        else:
            response = await adapter.test()
        record_result(session, row, response=response, actor=actor)
    except ProviderError as exc:
        record_result(session, row, error=exc, actor=actor)
    except Exception:
        record_result(
            session,
            row,
            error=ProviderError("Provider connection or response validation failed"),
            actor=actor,
        )
    return provider_payload(session, row, key)
