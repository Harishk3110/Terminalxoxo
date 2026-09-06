"""Auditable accounting components derived from a completed ledger replay."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any

from .cash import CashMovement
from .money import ONE, ZERO, decimal
from .types import AccountingPolicy, Entry


class PostingCategory(StrEnum):
    CAPITAL = "CAPITAL"
    INCOME = "INCOME"
    FEE = "FEE"
    ACCRUAL = "ACCRUAL"
    LIABILITY = "LIABILITY"


ASSET_BUCKETS = frozenset({"accrued_income", "receivables"})
LIABILITY_BUCKETS = frozenset({"payables", "accrued_fees", "other_liabilities"})
BALANCE_BUCKETS = ASSET_BUCKETS | LIABILITY_BUCKETS


@dataclass(frozen=True)
class CurrencyMark:
    rate: Decimal | None
    provenance: Mapping[str, Any]

    def __post_init__(self) -> None:
        if self.rate is not None:
            decimal(self.rate, "valuation FX", positive=True)


@dataclass(frozen=True)
class BalanceAdjustment:
    id: str
    effective_date: date
    bucket: str
    currency: str
    amount: Decimal
    reason: str

    def __post_init__(self) -> None:
        if self.bucket not in BALANCE_BUCKETS:
            raise ValueError("Unknown NAV balance bucket")
        decimal(self.amount, "balance adjustment")


@dataclass(frozen=True)
class AccountingPosting:
    key: str
    category: PostingCategory
    kind: str
    effective_date: date
    currency: str
    native_amount: Decimal
    fx_rate: Decimal | None
    transaction_id: str | None = None
    account_id: str | None = None
    instrument_id: str | None = None
    adjustment_id: str | None = None
    settlement_date: date | None = None
    capitalized_native: Decimal = ZERO
    provenance: Mapping[str, Any] = field(default_factory=dict)

    @property
    def base_amount(self) -> Decimal | None:
        return self.native_amount * self.fx_rate if self.fx_rate is not None else None

    @property
    def capitalized_base(self) -> Decimal | None:
        return self.capitalized_native * self.fx_rate if self.fx_rate is not None else None

    def payload(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "category": self.category.value,
            "kind": self.kind,
            "effective_date": self.effective_date.isoformat(),
            "currency": self.currency,
            "native_amount": str(self.native_amount),
            "fx_rate": str(self.fx_rate) if self.fx_rate is not None else None,
            "base_amount": str(self.base_amount) if self.base_amount is not None else None,
            "transaction_id": self.transaction_id,
            "account_id": self.account_id,
            "instrument_id": self.instrument_id,
            "adjustment_id": self.adjustment_id,
            "settlement_date": self.settlement_date.isoformat() if self.settlement_date else None,
            "capitalized_native": str(self.capitalized_native),
            "capitalized_base": str(self.capitalized_base)
            if self.capitalized_base is not None
            else None,
            "provenance": dict(self.provenance),
        }


def _transaction_posting(
    entry: Entry,
    category: PostingCategory,
    kind: str,
    amount: Decimal,
    capitalized: Decimal = ZERO,
) -> AccountingPosting:
    return AccountingPosting(
        key=f"{entry.id}:{kind}",
        category=category,
        kind=kind,
        effective_date=entry.day,
        currency=entry.currency,
        native_amount=amount,
        fx_rate=entry.fx,
        transaction_id=entry.id,
        account_id=entry.account_id,
        instrument_id=entry.instrument_id,
        settlement_date=entry.settlement,
        capitalized_native=capitalized,
        provenance={
            "basis": "RECORDED TRANSACTION FX",
            "source": entry.metadata.get("fx_source"),
            "external_reference": entry.metadata.get("external_reference"),
        },
    )


def transaction_postings(entry: Entry, policy: AccountingPolicy) -> list[AccountingPosting]:
    entry.validate()
    rows: list[AccountingPosting] = []
    if entry.kind in {"DEPOSIT", "WITHDRAWAL", "TRANSFER_IN", "TRANSFER_OUT"}:
        sign = ONE if entry.kind in {"DEPOSIT", "TRANSFER_IN"} else -ONE
        rows.append(
            _transaction_posting(entry, PostingCategory.CAPITAL, entry.kind, sign * entry.gross)
        )
    if entry.kind in {"DIVIDEND", "INTEREST"}:
        rows.append(_transaction_posting(entry, PostingCategory.INCOME, entry.kind, entry.gross))
    if entry.kind in {"COMMISSION", "FEE", "TAX"}:
        # Standalone expenses consume amount OR charges, exactly as the replay service does.
        rows.append(
            _transaction_posting(
                entry, PostingCategory.FEE, entry.kind, entry.gross or entry.charges
            )
        )
        return rows
    capitalizable = entry.kind in {"BUY", "SELL", "SHORT", "COVER"}
    for kind, amount, configured in (
        ("COMMISSION", entry.commission, policy.capitalize_commissions),
        ("FEE", entry.fee, policy.capitalize_fees),
        ("TAX", entry.tax, False),
    ):
        if amount:
            rows.append(
                _transaction_posting(
                    entry,
                    PostingCategory.FEE,
                    kind,
                    amount,
                    amount if capitalizable and configured else ZERO,
                )
            )
    return rows


def outstanding_postings(
    movements: Iterable[CashMovement],
    adjustments: Iterable[BalanceAdjustment],
    as_of: date,
    marks: Mapping[str, CurrencyMark],
) -> list[AccountingPosting]:
    rows: list[AccountingPosting] = []
    missing = CurrencyMark(None, {"source": "UNAVAILABLE", "data_state": "UNAVAILABLE"})
    for movement in movements:
        if not movement.trade_date <= as_of < movement.settlement_date or not movement.amount:
            continue
        mark = marks.get(movement.currency, missing)
        payable = movement.amount < ZERO
        rows.append(
            AccountingPosting(
                key=f"{movement.transaction_id}:PENDING:{movement.description}",
                category=PostingCategory.LIABILITY if payable else PostingCategory.ACCRUAL,
                kind="payables" if payable else "receivables",
                effective_date=movement.trade_date,
                currency=movement.currency,
                native_amount=abs(movement.amount),
                fx_rate=mark.rate,
                transaction_id=movement.transaction_id,
                account_id=movement.account_id,
                settlement_date=movement.settlement_date,
                provenance={
                    **mark.provenance,
                    "basis": "PENDING SETTLEMENT",
                    "leg": movement.description,
                },
            )
        )
    for adjustment in adjustments:
        if adjustment.effective_date > as_of:
            continue
        mark = marks.get(adjustment.currency, missing)
        rows.append(
            AccountingPosting(
                key=f"{adjustment.id}:BALANCE",
                category=PostingCategory.ACCRUAL
                if adjustment.bucket in ASSET_BUCKETS
                else PostingCategory.LIABILITY,
                kind=adjustment.bucket,
                effective_date=adjustment.effective_date,
                currency=adjustment.currency,
                native_amount=adjustment.amount,
                fx_rate=mark.rate,
                adjustment_id=adjustment.id,
                provenance={
                    **mark.provenance,
                    "basis": "BALANCE ADJUSTMENT",
                    "reason": adjustment.reason,
                },
            )
        )
    return rows


def summarize_postings(rows: Iterable[AccountingPosting]) -> dict[str, Decimal | None]:
    totals: dict[str, Decimal | None] = {
        "external_flows": ZERO,
        "income": ZERO,
        "fees_paid": ZERO,
        "taxes": ZERO,
        "capitalized_charges": ZERO,
        "expensed_fees": ZERO,
        **{bucket: ZERO for bucket in sorted(BALANCE_BUCKETS)},
    }

    def add(key: str, value: Decimal | None) -> None:
        previous = totals[key]
        totals[key] = previous + value if previous is not None and value is not None else None

    for row in rows:
        if row.category == PostingCategory.CAPITAL:
            add("external_flows", row.base_amount)
        elif row.category == PostingCategory.INCOME:
            add("income", row.base_amount)
        elif row.category == PostingCategory.FEE:
            if row.kind == "TAX":
                add("taxes", row.base_amount)
            else:
                add("fees_paid", row.base_amount)
                add("capitalized_charges", row.capitalized_base)
                add(
                    "expensed_fees",
                    (row.native_amount - row.capitalized_native) * row.fx_rate
                    if row.fx_rate is not None
                    else None,
                )
        else:
            add(row.kind, row.base_amount)
    return totals
