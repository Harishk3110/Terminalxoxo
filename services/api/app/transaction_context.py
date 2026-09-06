"""Validated trade provenance without inventing timestamps or broker confirmation."""

from datetime import UTC, date, datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator


class TransactionContext(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_timestamp: AwareDatetime | None = None
    external_reference: str | None = Field(default=None, max_length=160)
    broker_execution_id: str | None = Field(default=None, max_length=160)
    strategy_id: str | None = Field(default=None, max_length=36)
    thesis_id: str | None = Field(default=None, max_length=36)

    @field_validator("trade_timestamp")
    @classmethod
    def timestamp_in_utc(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        value = value.astimezone(UTC)
        if value > datetime.now(UTC):
            raise ValueError("Trade timestamp cannot be in the future")
        return value

    @field_validator("external_reference", "broker_execution_id", "strategy_id", "thesis_id")
    @classmethod
    def optional_identifier(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized.isprintable() and normalized:
            raise ValueError("Reference identifiers cannot contain control characters")
        return normalized or None


def record_context(
    payload: dict[str, Any],
    metadata: dict[str, Any],
    trade_date: date,
) -> TransactionContext:
    values: dict[str, Any] = {}
    for name in TransactionContext.model_fields:
        value = payload.get(name)
        if value is None:
            value = metadata.get(name)
        if value is None and name == "broker_execution_id":
            value = metadata.get("execution_id")
        if value is not None:
            values[name] = value
    context = TransactionContext.model_validate(values)
    if context.trade_timestamp is not None:
        # Exchange trade dates can differ from UTC dates, but not by multiple days.
        if abs((context.trade_timestamp.date() - trade_date).days) > 1:
            raise ValueError("Trade timestamp is inconsistent with the supplied trade date")
    metadata.update(context.model_dump(mode="json"))
    metadata["execution_id"] = context.broker_execution_id
    metadata.pop("created_by", None)
    metadata.pop("actor_user_id", None)
    return context


def context_payload(metadata: dict[str, Any], creator_id: str | None) -> dict[str, Any]:
    raw_timestamp = metadata.get("trade_timestamp")
    timestamp: str | None = None
    warnings: list[str] = []
    if raw_timestamp is not None:
        try:
            validated = TransactionContext(trade_timestamp=raw_timestamp)
            timestamp = validated.trade_timestamp.isoformat() if validated.trade_timestamp else None
        except ValueError:
            warnings.append("Legacy trade timestamp is unvalidated; original metadata retained")
    references: dict[str, str | None] = {}
    for name in ("external_reference", "broker_execution_id", "strategy_id", "thesis_id"):
        raw = metadata.get(name)
        if name == "broker_execution_id" and raw is None:
            raw = metadata.get("execution_id")
        try:
            validated_reference = TransactionContext.model_validate({name: raw})
            references[name] = getattr(validated_reference, name)
        except ValueError:
            references[name] = None
            warnings.append(f"Legacy {name} is unvalidated; original metadata retained")
    return {
        "trade_timestamp": timestamp,
        "trade_timestamp_state": "RECORDED" if timestamp else "NOT_RECORDED",
        "trade_timestamp_usage": "PROVENANCE_ONLY; same-day replay retains ledger record order",
        **references,
        "created_by": creator_id,
        "creator_state": "AUDIT_LOG" if creator_id else "NOT_RECORDED",
        "context_warnings": warnings,
    }
