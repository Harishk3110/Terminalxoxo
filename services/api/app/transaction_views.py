"""Transaction resource views reuse effective ledger replay, without market-price queries."""

from typing import Any

from sqlalchemy.orm import Session

from .portfolio_domain.ledger import LedgerState
from .portfolio_domain.transaction_cash import enrich_cash_effects
from .portfolio_domain.types import AccountingPolicy
from .portfolio_valuation import PortfolioValuationService, load_entries


def transaction_views(session: Session, portfolio_key: str) -> list[dict[str, Any]]:
    portfolio, profile = PortfolioValuationService(session).portfolio(portfolio_key)
    entries, payloads = load_entries(session, portfolio.id)
    ledger = LedgerState(policy=AccountingPolicy.from_config(profile.configuration))
    for entry in entries:
        ledger.apply(entry)
    enrich_cash_effects(payloads, entries, ledger.cash_service.movements)
    return payloads
