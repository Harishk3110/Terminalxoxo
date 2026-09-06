"""Real database correction workflows with foreign keys and immutable prior runs."""

from datetime import date
from decimal import Decimal as D

import pytest
from app import models
from app.ledger_contracts import (
    AccountingPolicyRequest,
    AmendmentRequest,
    RevisionRequest,
    TransactionChanges,
)
from app.ledger_revisions import PortfolioTransactionService, RevisionConflict
from app.portfolio_operations import PortfolioLedgerService
from app.portfolio_resources import PortfolioResourceService
from app.portfolio_valuation import PortfolioValuationService, load_entries
from sqlalchemy import func, select
from sqlalchemy.orm import Session

END = date(2026, 1, 9)


def add_buy(session: Session, quantity: str = "10", price: str = "100") -> str:
    result = PortfolioLedgerService(session).add(
        {
            "transaction_type": "BUY",
            "trade_date": "2026-01-06",
            "symbol": "AAA",
            "quantity": quantity,
            "price": price,
        },
        "book",
    )
    session.commit()
    return str(result["id"])


def amendment(**changes: str) -> AmendmentRequest:
    return AmendmentRequest(
        expected_version=1,
        reason="Correct source statement",
        changes=TransactionChanges.model_validate(changes),
    )


def test_amendment_updates_effective_ledger_not_original_record(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    original = ledger_session.get(models.PortfolioTransaction, identifier)
    assert original is not None
    created_at = original.created_at
    result = PortfolioTransactionService(ledger_session).revise(
        "book", identifier, amendment(quantity="8", notes="Corrected allocation")
    )
    ledger_session.commit()
    assert result["audit_version"] == 2
    ledger_session.refresh(original)
    assert original.quantity == D("10")
    assert original.created_at == created_at
    entries, payloads = load_entries(ledger_session, "book")
    effective = next(item for item in entries if item.id == identifier)
    assert effective.quantity == D("8")
    assert effective.amount == D("800")
    payload = next(item for item in payloads if item["id"] == identifier)
    assert payload["notes"] == "Corrected allocation"
    assert payload["audit_version"] == 2
    assert payload["ledger_state"] == "ACTIVE"
    assert D(payload["base_value"]) == D("800")


def test_revision_keeps_before_after_reason_and_audit_event(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    service = PortfolioTransactionService(ledger_session)
    service.revise("book", identifier, amendment(price="101.25"))
    ledger_session.commit()
    history = service.history("book", identifier)
    assert len(history) == 1
    assert history[0]["action"] == "AMEND"
    assert history[0]["reason"] == "Correct source statement"
    assert D(history[0]["before"]["entry"]["price"]) == D("100")
    assert D(history[0]["after"]["entry"]["price"]) == D("101.25")
    audit = ledger_session.scalar(
        select(models.AuditLog).where(models.AuditLog.action == "LEDGER_TRANSACTION_AMEND")
    )
    assert audit is not None
    assert audit.resource_id == identifier
    assert audit.metadata_json["revision_id"] == history[0]["id"]


def test_optimistic_version_rejects_stale_editor(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    service = PortfolioTransactionService(ledger_session)
    service.revise("book", identifier, amendment(quantity="8"))
    ledger_session.commit()
    with pytest.raises(RevisionConflict, match="changed"):
        service.revise("book", identifier, amendment(quantity="7"))
    assert len(service.history("book", identifier)) == 1


def test_second_revision_starts_from_effective_first_revision(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    service = PortfolioTransactionService(ledger_session)
    service.revise("book", identifier, amendment(quantity="8"))
    ledger_session.commit()
    second = AmendmentRequest(
        expected_version=2,
        reason="Correct execution price",
        changes=TransactionChanges(price=D("105")),
    )
    result = service.revise("book", identifier, second)
    ledger_session.commit()
    effective = next(
        item for item in load_entries(ledger_session, "book")[0] if item.id == identifier
    )
    assert effective.quantity == D("8")
    assert effective.price == D("105")
    assert effective.amount == D("840")
    assert result["audit_version"] == 3
    assert [row["version"] for row in service.history("book", identifier)] == [2, 3]


def test_void_is_tombstone_and_original_transaction_remains(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    service = PortfolioTransactionService(ledger_session)
    service.revise(
        "book", identifier, RevisionRequest(expected_version=1, reason="Duplicate manual entry")
    )
    ledger_session.commit()
    entries, rows = load_entries(ledger_session, "book")
    assert identifier not in {item.id for item in entries}
    assert next(row for row in rows if row["id"] == identifier)["ledger_state"] == "VOID"
    assert ledger_session.get(models.PortfolioTransaction, identifier) is not None
    assert ledger_session.scalar(select(func.count(models.TransactionDetail.id))) == 2
    value = PortfolioValuationService(ledger_session).calculate("book", END)
    assert value["portfolio"]["nav"] == "10000.00"
    assert value["positions"] == []


def test_voided_entry_cannot_be_amended_or_voided_again(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    service = PortfolioTransactionService(ledger_session)
    service.revise(
        "book", identifier, RevisionRequest(expected_version=1, reason="Duplicate manual entry")
    )
    ledger_session.commit()
    with pytest.raises(RevisionConflict, match="Voided"):
        service.revise(
            "book", identifier, RevisionRequest(expected_version=2, reason="Attempt repeated void")
        )


def test_correction_replays_later_sales_and_rejects_oversell(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    PortfolioLedgerService(ledger_session).add(
        {
            "transaction_type": "SELL",
            "trade_date": "2026-01-07",
            "symbol": "AAA",
            "quantity": "8",
            "price": "115",
        },
        "book",
    )
    ledger_session.commit()
    with pytest.raises(ValueError, match="exceeds"):
        PortfolioTransactionService(ledger_session).revise(
            "book", identifier, amendment(quantity="5")
        )
    assert ledger_session.scalar(select(func.count(models.TransactionRevision.id))) == 0
    assert (
        ledger_session.scalar(
            select(func.count(models.AuditLog.id)).where(
                models.AuditLog.action == "LEDGER_TRANSACTION_AMEND"
            )
        )
        == 0
    )
    assert (
        PortfolioValuationService(ledger_session).calculate("book", END)["positions"][0]["quantity"]
        == "2.00000000"
    )


def test_voiding_purchase_with_later_disposal_is_rejected(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    PortfolioLedgerService(ledger_session).add(
        {
            "transaction_type": "SELL",
            "trade_date": "2026-01-07",
            "symbol": "AAA",
            "quantity": "2",
            "price": "115",
        },
        "book",
    )
    ledger_session.commit()
    with pytest.raises(ValueError, match="exceeds"):
        PortfolioTransactionService(ledger_session).revise(
            "book",
            identifier,
            RevisionRequest(expected_version=1, reason="Remove opening transaction"),
        )
    assert ledger_session.scalar(select(func.count(models.TransactionRevision.id))) == 0


def test_cross_portfolio_correction_does_not_find_transaction(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    with pytest.raises(ValueError, match="does not belong"):
        PortfolioTransactionService(ledger_session).revise(
            "different-book", identifier, amendment(price="120")
        )
    assert not PortfolioTransactionService(ledger_session).history("book", identifier)


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"quantity": "10"},
        {"fx_rate_to_base": "1.2"},
        {"trade_date": "2099-01-01"},
        {"settle_date": "2026-01-05"},
    ],
)
def test_invalid_or_noop_correction_does_not_append_history(
    ledger_session: Session, changes: dict[str, str]
) -> None:
    identifier = add_buy(ledger_session)
    with pytest.raises(ValueError):
        PortfolioTransactionService(ledger_session).revise("book", identifier, amendment(**changes))
    assert not PortfolioTransactionService(ledger_session).history("book", identifier)


def test_revision_rollback_drops_revision_and_audit_together(ledger_session: Session) -> None:
    identifier = add_buy(ledger_session)
    PortfolioTransactionService(ledger_session).revise("book", identifier, amendment(quantity="8"))
    ledger_session.rollback()
    assert ledger_session.scalar(select(func.count(models.TransactionRevision.id))) == 0
    assert (
        ledger_session.scalar(
            select(func.count(models.AuditLog.id)).where(
                models.AuditLog.action == "LEDGER_TRANSACTION_AMEND"
            )
        )
        == 0
    )
    effective = next(
        item for item in load_entries(ledger_session, "book")[0] if item.id == identifier
    )
    assert effective.quantity == D("10")


def test_old_valuation_and_lot_snapshot_are_immutable_after_correction(
    ledger_session: Session,
) -> None:
    identifier = add_buy(ledger_session)
    valuations = PortfolioValuationService(ledger_session)
    first = valuations.latest("book", end=END)
    first_id = first["valuation_run_id"]
    old_lot = ledger_session.scalar(
        select(models.PositionLot).where(models.PositionLot.valuation_run_id == first_id)
    )
    assert old_lot is not None
    assert old_lot.quantity == D("10")
    PortfolioTransactionService(ledger_session).revise("book", identifier, amendment(quantity="8"))
    ledger_session.commit()
    second = valuations.latest("book", end=END)
    assert first_id != second["valuation_run_id"]
    assert first["portfolio"]["nav"] == "10200.00"
    assert second["portfolio"]["nav"] == "10160.00"
    ledger_session.refresh(old_lot)
    assert old_lot.quantity == D("10")
    old_run = ledger_session.get(models.PortfolioValuationRun, first_id)
    assert old_run is not None
    assert old_run.payload["portfolio"]["nav"] == "10200.00"
    assert second["reconciliation"]["state"] == "BALANCED"


def test_policy_change_replays_basis_and_keeps_nav_constant(ledger_session: Session) -> None:
    add_buy(ledger_session)
    PortfolioLedgerService(ledger_session).add(
        {
            "transaction_type": "BUY",
            "trade_date": "2026-01-07",
            "symbol": "AAA",
            "quantity": "10",
            "price": "110",
            "commission": "2",
        },
        "book",
    )
    PortfolioLedgerService(ledger_session).add(
        {
            "transaction_type": "SELL",
            "trade_date": "2026-01-08",
            "symbol": "AAA",
            "quantity": "5",
            "price": "120",
            "commission": "3",
        },
        "book",
    )
    ledger_session.commit()
    before = PortfolioValuationService(ledger_session).latest("book", end=END)
    request = AccountingPolicyRequest(
        method="FIFO",
        capitalize_commissions=True,
        capitalize_fees=True,
        reason="Adopt explicit lot policy",
    )
    PortfolioResourceService(ledger_session).change_policy("book", request, None)
    ledger_session.commit()
    after = PortfolioValuationService(ledger_session).latest("book", end=END)
    assert before["portfolio"]["nav"] == after["portfolio"]["nav"]
    assert before["positions"][0]["realised_pnl"] == "75.00"
    assert after["positions"][0]["realised_pnl"] == "97.00"
    assert after["positions"][0]["total_pnl"] == before["positions"][0]["total_pnl"]
    assert after["cost_basis"]["capitalized_charges"] == "5.0000000000000000"
    assert after["reconciliation"]["difference"] == "0.00"
    assert before["valuation_run_id"] != after["valuation_run_id"]
    assert ledger_session.scalar(select(func.count(models.PositionLotMatch.id))) == 3
