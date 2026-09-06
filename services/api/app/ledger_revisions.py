"""Append-only corrections, optimistic versions and chronological replay validation."""

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .ledger_contracts import AmendmentRequest, EntryRecord, RevisionRequest
from .ledger_storage import validate_corrected_storage
from .portfolio_domain.ledger import LedgerState
from .portfolio_domain.money import stored_decimal
from .portfolio_domain.types import SECURITY_MOVEMENTS, AccountingPolicy, Entry


class RevisionConflict(ValueError):
    pass


def apply_revisions(
    session: Session,
    portfolio_id: str,
    entries: list[Entry],
    payloads: list[dict[str, Any]],
) -> tuple[list[Entry], list[dict[str, Any]]]:
    rows = session.scalars(
        select(models.TransactionRevision)
        .where(models.TransactionRevision.portfolio_id == portfolio_id)
        .order_by(models.TransactionRevision.version)
    ).all()
    latest = {row.transaction_id: row for row in rows}
    effective = []
    for entry, payload in zip(entries, payloads, strict=True):
        revision = latest.get(entry.id)
        payload["audit_version"] = revision.version if revision else 1
        payload["ledger_state"] = "VOID" if revision and revision.action == "VOID" else "ACTIVE"
        if revision:
            payload["revision_id"] = revision.id
            payload["revision_reason"] = revision.reason
            payload["updated_at"] = revision.created_at.isoformat()
            snapshot = revision.before if revision.action == "VOID" else revision.after
            entry = EntryRecord.model_validate(snapshot["entry"]).to_entry()
            payload.update(entry_payload(entry))
            payload["metadata"] = entry.metadata
            payload["notes"] = snapshot.get("notes")
            if revision.action == "VOID":
                continue
        effective.append(entry)
    effective.sort(key=lambda entry: entry.day)
    return effective, payloads


def entry_payload(entry: Entry) -> dict[str, Any]:
    return {
        "trade_date": entry.day.isoformat(),
        "settle_date": entry.settlement.isoformat(),
        "quantity": str(entry.quantity),
        "price": str(entry.price),
        "gross_amount": str(entry.gross),
        "fee": str(entry.fee),
        "commission": str(entry.commission),
        "tax": str(entry.tax),
        "fx_rate_to_base": str(entry.fx),
        "base_value": str(entry.gross * entry.fx),
    }


class PortfolioTransactionService:
    def __init__(self, session: Session):
        self.session = session

    def revise(
        self,
        portfolio_id: str,
        transaction_id: str,
        request: RevisionRequest,
        *,
        actor: str | None = None,
    ) -> dict[str, Any]:
        from .portfolio_valuation import load_entries

        transaction = self.session.scalar(
            select(models.PortfolioTransaction)
            .where(
                models.PortfolioTransaction.id == transaction_id,
                models.PortfolioTransaction.portfolio_id == portfolio_id,
            )
            .with_for_update()
        )
        if transaction is None:
            raise ValueError("Transaction does not belong to portfolio")
        profile = self.session.scalar(
            select(models.PortfolioProfile).where(
                models.PortfolioProfile.portfolio_id == portfolio_id
            )
        )
        if profile is None:
            raise ValueError("Portfolio is not enabled for audited accounting")
        entries, payloads = load_entries(self.session, portfolio_id)
        payload = next(row for row in payloads if row["id"] == transaction_id)
        if payload["audit_version"] != request.expected_version:
            raise RevisionConflict("Transaction changed; reload its current audit version")
        if payload["ledger_state"] == "VOID":
            raise RevisionConflict(
                "Voided transactions cannot be revised; record a new transaction"
            )
        entry = next(item for item in entries if item.id == transaction_id)
        before = {
            "entry": EntryRecord.from_entry(entry).model_dump(mode="json"),
            "notes": payload.get("notes"),
        }
        action = "AMEND" if isinstance(request, AmendmentRequest) else "VOID"
        after: dict[str, Any]
        if isinstance(request, AmendmentRequest):
            updated, notes = self._amend(entry, request, payload.get("notes"))
            validate_corrected_storage(self.session, updated)
            portfolio = self.session.get(models.Portfolio, portfolio_id)
            if portfolio and updated.currency == portfolio.base_currency and updated.fx != 1:
                raise ValueError("Base-currency transaction FX must equal one")
            candidate = [updated if item.id == transaction_id else item for item in entries]
            after = {
                "entry": EntryRecord.from_entry(updated).model_dump(mode="json"),
                "notes": notes,
            }
            if updated == entry and notes == payload.get("notes"):
                raise ValueError("Correction contains no effective change")
        else:
            candidate = [item for item in entries if item.id != transaction_id]
            after = {"void": True}
            if not candidate:
                raise ValueError("Cannot void the only ledger entry; archive the portfolio instead")
        state = LedgerState(policy=AccountingPolicy.from_config(profile.configuration))
        for item in sorted(candidate, key=lambda value: value.day):
            state.apply(item)
        revision = models.TransactionRevision(
            portfolio_id=portfolio_id,
            transaction_id=transaction_id,
            version=request.expected_version + 1,
            action=action,
            reason=request.reason,
            actor_user_id=actor,
            before=before,
            after=after,
        )
        self.session.add(revision)
        self.session.flush()
        self.session.add(
            models.AuditLog(
                action=f"LEDGER_TRANSACTION_{action}",
                resource_type="portfolio_transaction",
                resource_id=transaction_id,
                actor_user_id=actor,
                correlation_id=str(uuid4()),
                metadata_json={
                    "revision_id": revision.id,
                    "version": revision.version,
                    "reason": request.reason,
                    "before": before,
                    "after": after,
                },
            )
        )
        self.session.flush()
        return {
            "transaction_id": transaction_id,
            "revision_id": revision.id,
            "audit_version": revision.version,
            "ledger_state": "VOID" if action == "VOID" else "ACTIVE",
        }

    @staticmethod
    def _amend(
        entry: Entry, request: AmendmentRequest, notes: str | None
    ) -> tuple[Entry, str | None]:
        changes = request.changes.model_dump(exclude_unset=True)
        if not changes:
            raise ValueError("Correction requires at least one changed field")
        if any(value is None and key != "notes" for key, value in changes.items()):
            raise ValueError("Accounting fields cannot be cleared")
        updated_notes = changes.pop("notes", notes)
        aliases = {"trade_date": "day", "fx_rate_to_base": "fx"}
        fields = {aliases.get(key, key): value for key, value in changes.items()}
        updated = replace(entry, **fields)
        if updated.day > datetime.now(UTC).date():
            raise ValueError("Future-dated corrections are not accepted")
        if updated.kind in SECURITY_MOVEMENTS and updated.instrument_id and "amount" not in fields:
            updated = replace(updated, amount=updated.quantity * updated.price * updated.multiplier)
        stored_decimal(updated.gross, "corrected gross amount", nonnegative=True)
        updated.validate()
        if updated.fx != entry.fx:
            metadata = dict(updated.metadata)
            metadata.pop("fx_recording", None)
            metadata["fx_source"] = "AUDITED MANUAL CORRECTION"
            metadata["fx_correction"] = {
                "previous_rate": str(entry.fx),
                "recorded_rate": str(updated.fx),
                "reason": request.reason,
            }
            updated = replace(updated, metadata=metadata)
        return updated, updated_notes

    def history(self, portfolio_id: str, transaction_id: str) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(models.TransactionRevision)
            .where(
                models.TransactionRevision.portfolio_id == portfolio_id,
                models.TransactionRevision.transaction_id == transaction_id,
            )
            .order_by(models.TransactionRevision.version)
        ).all()
        return [
            {
                "id": row.id,
                "version": row.version,
                "action": row.action,
                "reason": row.reason,
                "actor_user_id": row.actor_user_id,
                "created_at": row.created_at.isoformat(),
                "before": row.before,
                "after": row.after,
            }
            for row in rows
        ]
