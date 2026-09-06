from .provider_data import provider_payload, record_result
from .providers.http import ProviderError, Response


async def probe(session, row, key, adapter, actor=None, correlation_id="provider-test"):
    if not row.enabled or not row.configured or row.connection_state == "REVOKED":
        raise ValueError("Provider is disabled, revoked or not configured")
    try:
        if key == "fred":
            payload = await adapter.series_metadata("GDP", correlation_id)
            response = Response(payload, b"", "", payload.get("_knk_latency_ms", 0), None)
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
