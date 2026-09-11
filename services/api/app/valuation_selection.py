"""Explicit historical or saved valuation selection without a freshness override."""

from datetime import UTC, date, datetime
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ValuationSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    valuation_date: date | None = None
    valuation_run_id: str | None = Field(default=None, min_length=1, max_length=80)

    @field_validator("valuation_date", mode="before")
    @classmethod
    def calendar_date(cls, value: object) -> date | None:
        if value is None:
            return None
        if isinstance(value, date) and not isinstance(value, datetime):
            return value
        if isinstance(value, str):
            parsed = date.fromisoformat(value)
            if parsed.isoformat() == value:
                return parsed
        raise ValueError("Valuation date must be YYYY-MM-DD")

    @model_validator(mode="after")
    def coherent(self) -> Self:
        if self.valuation_run_id and self.valuation_date is not None:
            raise ValueError("Choose a saved valuation run or a valuation date, not both")
        if self.valuation_date and self.valuation_date > datetime.now(UTC).date():
            raise ValueError("Valuation date cannot be in the future")
        return self
