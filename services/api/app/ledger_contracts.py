"""Validated contracts for accounting policy and append-only ledger changes."""

from dataclasses import asdict
from datetime import date
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .portfolio_domain.money import stored_decimal
from .portfolio_domain.types import AccountingPolicy, CostMethod, Entry


class EntryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    day: date
    kind: str
    currency: str
    quantity: Decimal
    price: Decimal
    fx: Decimal
    amount: Decimal
    fee: Decimal
    commission: Decimal
    tax: Decimal
    instrument_id: str | None
    multiplier: Decimal
    metadata: dict[str, Any]
    settle_date: date | None
    account_id: str | None

    @classmethod
    def from_entry(cls, entry: Entry) -> "EntryRecord":
        return cls.model_validate(asdict(entry))

    def to_entry(self) -> Entry:
        entry = Entry(**self.model_dump())
        entry.validate()
        return entry


class TransactionChanges(BaseModel):
    model_config = ConfigDict(extra="forbid")
    trade_date: date | None = None
    settle_date: date | None = None
    quantity: Decimal | None = Field(default=None, ge=0)
    price: Decimal | None = Field(default=None, ge=0)
    amount: Decimal | None = Field(default=None, ge=0)
    fee: Decimal | None = Field(default=None, ge=0)
    commission: Decimal | None = Field(default=None, ge=0)
    tax: Decimal | None = Field(default=None, ge=0)
    fx_rate_to_base: Decimal | None = Field(default=None, gt=0)
    notes: str | None = Field(default=None, max_length=10000)

    @field_validator("quantity", "price", "amount", "fee", "commission", "tax", "fx_rate_to_base")
    @classmethod
    def bounded(cls, value: Decimal | None) -> Decimal | None:
        return stored_decimal(value, "corrected accounting value") if value is not None else None


class RevisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=1)
    reason: str = Field(min_length=5, max_length=2000)

    @field_validator("reason")
    @classmethod
    def meaningful_reason(cls, value: str) -> str:
        if len(value.strip()) < 5:
            raise ValueError("A meaningful correction reason is required")
        return value.strip()


class AmendmentRequest(RevisionRequest):
    changes: TransactionChanges


class AccountingPolicyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: CostMethod
    capitalize_commissions: bool = Field(strict=True)
    capitalize_fees: bool = Field(strict=True)
    reason: str = Field(min_length=5, max_length=2000)

    @field_validator("reason")
    @classmethod
    def policy_reason(cls, value: str) -> str:
        return RevisionRequest.meaningful_reason(value)

    def policy(self) -> AccountingPolicy:
        return AccountingPolicy(self.method, self.capitalize_commissions, self.capitalize_fees)


class PortfolioCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z][A-Z0-9_]+$")
    name: str = Field(min_length=2, max_length=200)
    base_currency: str = Field(default="SGD", pattern=r"^[A-Z]{3}$")
    reference_capital: Decimal = Field(gt=0, le=Decimal("1e12"))
    opening_date: date
    benchmark: str = Field(default="SPY", min_length=1, max_length=40)
    allow_short: bool = Field(default=False, strict=True)
    method: CostMethod = CostMethod.AVERAGE
    capitalize_commissions: bool = Field(default=True, strict=True)
    capitalize_fees: bool = Field(default=False, strict=True)

    @field_validator("name")
    @classmethod
    def nonblank_name(cls, value: str) -> str:
        if len(value.strip()) < 2:
            raise ValueError("Portfolio name must contain at least two characters")
        return value.strip()
