"""Capital specification changes append corrections, not destructive ledger rewrites."""

from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app import models
from app.portfolio_seed import REFERENCE_CAPITAL, upgrade_demo_capital
from app.portfolio_valuation import load_entries


def old_demo(session):
    portfolio = session.get(models.Portfolio, "book")
    portfolio.reference_capital = Decimal("70000")
    profile = session.scalar(select(models.PortfolioProfile))
    profile.code, profile.is_demo = "KNK_MAIN", True
    transaction = session.get(models.PortfolioTransaction, "deposit")
    transaction.source = "KNK_MAIN_DEMO"
    detail = session.scalar(select(models.TransactionDetail))
    detail.gross_amount = detail.base_value = Decimal("70000")
    session.commit()
    return portfolio, profile, detail


def test_opening_capital_revision_preserves_original_and_is_idempotent(ledger_session):
    portfolio, profile, detail = old_demo(ledger_session)
    assert upgrade_demo_capital(ledger_session, portfolio, profile)
    ledger_session.commit()
    assert portfolio.reference_capital == REFERENCE_CAPITAL == Decimal("100000")
    assert detail.gross_amount == Decimal("70000")
    entries, payloads = load_entries(ledger_session, portfolio.id)
    assert entries[0].amount == Decimal("100000")
    assert payloads[0]["audit_version"] == 2
    assert not upgrade_demo_capital(ledger_session, portfolio, profile)
    assert ledger_session.scalar(select(func.count(models.TransactionRevision.id))) == 1
    assert ledger_session.scalar(select(models.AuditLog).where(models.AuditLog.action == "DEMO_CAPITAL_SPECIFICATION_CORRECTED"))


@pytest.mark.parametrize("change", ["real", "renamed", "custom_capital", "manual_contribution", "revised_contribution"])
def test_capital_upgrade_never_overwrites_user_portfolios(ledger_session, change):
    portfolio, profile, detail = old_demo(ledger_session)
    if change == "real":
        profile.is_demo = False
    elif change == "renamed":
        profile.code = "USER_BOOK"
    elif change == "custom_capital":
        portfolio.reference_capital = Decimal("50000")
    elif change == "manual_contribution":
        ledger_session.get(models.PortfolioTransaction, "deposit").source = "MANUAL"
    else:
        detail.gross_amount = Decimal("70001")
    ledger_session.commit()
    assert not upgrade_demo_capital(ledger_session, portfolio, profile)
    assert ledger_session.scalar(select(func.count(models.TransactionRevision.id))) == 0
