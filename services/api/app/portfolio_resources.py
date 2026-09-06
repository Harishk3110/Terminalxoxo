"""Resource-oriented portfolio orchestration, separate from financial calculations."""

from datetime import UTC, date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .accounting_persistence import accounting_records
from .ledger_contracts import AccountingPolicyRequest, PortfolioCreateRequest
from .portfolio_domain.ledger import LedgerState
from .portfolio_domain.postings import PostingCategory
from .portfolio_domain.types import TRANSACTION_TYPES, AccountingPolicy
from .portfolio_operations import CURRENCIES, PortfolioLedgerService
from .portfolio_valuation import PortfolioValuationService, load_entries
from .transaction_views import transaction_views


class PortfolioNotFound(ValueError):
    pass


class PortfolioResourceService:
    def __init__(self, session: Session):
        self.session = session

    def resolve(self, key: str) -> tuple[models.Portfolio, models.PortfolioProfile]:
        pair = self.session.execute(
            select(models.Portfolio, models.PortfolioProfile)
            .join(
                models.PortfolioProfile,
                models.PortfolioProfile.portfolio_id == models.Portfolio.id,
            )
            .where((models.Portfolio.id == key) | (models.PortfolioProfile.code == key))
        ).one_or_none()
        if pair is None:
            raise PortfolioNotFound("Portfolio not found")
        return pair[0], pair[1]

    def metadata(self, key: str) -> dict[str, Any]:
        portfolio, profile = self.resolve(key)
        accounts = self.session.scalars(
            select(models.PortfolioAccount).where(
                models.PortfolioAccount.portfolio_id == portfolio.id
            )
        ).all()
        return {
            "id": portfolio.id,
            "code": profile.code,
            "name": portfolio.name,
            "base_currency": portfolio.base_currency,
            "reference_capital": str(portfolio.reference_capital),
            "is_demo": profile.is_demo,
            "is_default": portfolio.is_default,
            "configuration": profile.configuration,
            "accounting_policy": AccountingPolicy.from_config(profile.configuration).to_dict(),
            "accounts": [
                {
                    "id": account.id,
                    "name": account.display_name,
                    "type": account.account_type,
                    "provider": account.provider,
                }
                for account in accounts
            ],
        }

    def list_portfolios(self) -> list[dict[str, Any]]:
        identifiers = self.session.scalars(
            select(models.PortfolioProfile.portfolio_id).order_by(models.PortfolioProfile.code)
        ).all()
        return [self.metadata(identifier) for identifier in identifiers]

    def entry_options(self, key: str) -> dict[str, Any]:
        metadata = self.metadata(key)
        strategies = self.session.scalars(
            select(models.StrategyDefinition).order_by(models.StrategyDefinition.name)
        ).all()
        theses = self.session.scalars(
            select(models.InvestmentThesis).order_by(models.InvestmentThesis.title)
        ).all()
        return {
            "portfolio": metadata,
            "transaction_types": sorted(TRANSACTION_TYPES),
            "currencies": sorted(CURRENCIES),
            "strategies": [
                {"id": row.id, "name": row.name, "state": row.status} for row in strategies
            ],
            "theses": [
                {
                    "id": row.id,
                    "title": row.title,
                    "state": row.thesis_state,
                    "instrument_id": row.instrument_id,
                }
                for row in theses
            ],
        }

    def create(self, request: PortfolioCreateRequest, actor: str | None) -> dict[str, Any]:
        if request.opening_date > datetime.now(UTC).date():
            raise ValueError("Opening date cannot be in the future")
        if request.base_currency not in CURRENCIES:
            raise ValueError("Base currency is not configured")
        if (
            self.session.scalar(
                select(models.Instrument.id).where(models.Instrument.symbol == request.benchmark)
            )
            is None
        ):
            raise ValueError("Benchmark must be a known security")
        if request.code == "KNK_MAIN" or request.code.startswith("ARCHIVE_"):
            raise ValueError("Portfolio code is reserved")
        portfolio = models.Portfolio(
            name=request.name,
            base_currency=request.base_currency,
            reference_capital=request.reference_capital,
            is_default=False,
        )
        self.session.add(portfolio)
        self.session.flush()
        policy = AccountingPolicy(
            request.method, request.capitalize_commissions, request.capitalize_fees
        )
        profile = models.PortfolioProfile(
            portfolio_id=portfolio.id,
            code=request.code,
            is_demo=False,
            configuration={
                "accounting": policy.to_dict(),
                "benchmark": request.benchmark,
                "allow_short": request.allow_short,
                "price_mode": "AUTO",
            },
        )
        self.session.add(profile)
        self.session.add(
            models.PortfolioAccount(
                portfolio_id=portfolio.id,
                account_type="INTERNAL",
                display_name="Internal ledger",
                provider=None,
            )
        )
        self.session.flush()
        PortfolioLedgerService(self.session).add(
            {
                "transaction_type": "DEPOSIT",
                "trade_date": request.opening_date.isoformat(),
                "currency": request.base_currency,
                "amount": str(request.reference_capital),
                "notes": "Explicit opening capital contribution",
            },
            portfolio.id,
            actor=actor,
        )
        self._audit(
            "PORTFOLIO_CREATED",
            portfolio.id,
            actor,
            {"code": request.code, "accounting": policy.to_dict()},
        )
        return self.metadata(portfolio.id)

    def summary(self, key: str, end: date | None = None, *, force: bool = False) -> dict[str, Any]:
        if end is not None and end > datetime.now(UTC).date():
            raise ValueError("Valuation date cannot be in the future")
        portfolio, _ = self.resolve(key)
        return dict(
            PortfolioValuationService(self.session).latest(
                portfolio.id, end=end, force=force, commit=False
            )
        )

    def recalculate(self, key: str, end: date | None, actor: str | None) -> dict[str, Any]:
        result = self.summary(key, end, force=True)
        self._audit(
            "PORTFOLIO_RECALCULATED",
            result["portfolio"]["id"],
            actor,
            {
                "valuation_run_id": result["valuation_run_id"],
                "end": end.isoformat() if end else None,
            },
        )
        return result

    def accounting(
        self, key: str, run_id: str | None, category: PostingCategory | None
    ) -> dict[str, Any]:
        portfolio, _ = self.resolve(key)
        if run_id:
            run = self.session.get(models.PortfolioValuationRun, run_id)
            if run is None or run.portfolio_id != portfolio.id:
                raise PortfolioNotFound("Valuation run not found in portfolio")
            data = run.payload
        else:
            data = self.summary(portfolio.id)
            run_id = data["valuation_run_id"]
        if "accounting" not in data:
            return {
                "items": [],
                "state": "UNAVAILABLE",
                "valuation_run_id": run_id,
                "warnings": ["This historical run predates accounting subledger snapshots"],
            }
        return {
            "items": accounting_records(self.session, portfolio.id, str(run_id), category),
            "totals": data["accounting"]["totals"],
            "reconciliation": data["accounting"]["reconciliation"],
            "state": "AVAILABLE",
            "valuation_run_id": run_id,
            "category": category,
            "base_currency": portfolio.base_currency,
            "as_of": data["curve"][-1]["date"],
            "quality": data["quality"],
            "calculation_version": data["calculation_version"],
        }

    def transactions(self, key: str) -> list[dict[str, Any]]:
        portfolio, _ = self.resolve(key)
        return transaction_views(self.session, portfolio.id)

    def transaction(self, key: str, transaction_id: str) -> dict[str, Any]:
        item = next((row for row in self.transactions(key) if row["id"] == transaction_id), None)
        if item is None:
            raise PortfolioNotFound("Transaction not found in portfolio")
        return item

    def position(
        self, key: str, position_id: str, end: date | None = None, run_id: str | None = None
    ) -> dict[str, Any]:
        if run_id and end is not None:
            raise ValueError("Choose a saved valuation run or an end date, not both")
        if run_id:
            portfolio, _ = self.resolve(key)
            run = self.session.get(models.PortfolioValuationRun, run_id)
            if run is None or run.portfolio_id != portfolio.id:
                raise PortfolioNotFound("Valuation run not found in portfolio")
            data = run.payload
        else:
            data = self.summary(key, end)
        item = next((row for row in data["positions"] if row["instrument_id"] == position_id), None)
        if item is None:
            raise PortfolioNotFound("Open position not found in portfolio")
        return {
            **item,
            "lots": [row for row in data.get("lots", []) if row["instrument_id"] == position_id],
            "matches": [
                row for row in data.get("lot_matches", []) if row["instrument_id"] == position_id
            ],
            "valuation_run_id": data.get("valuation_run_id", run_id),
            "portfolio_id": data["portfolio"]["id"],
            "base_currency": data["portfolio"]["base_currency"],
            "valuation_date": data["curve"][-1]["date"],
            "calculation_version": data["calculation_version"],
            "calculated_at": data["calculated_at"],
            "accounting_policy": data["portfolio"].get("accounting_policy"),
            "measurement_state": "AVAILABLE" if "valuation_state" in item else "LEGACY_SNAPSHOT",
        }

    def change_policy(
        self, key: str, request: AccountingPolicyRequest, actor: str | None
    ) -> dict[str, Any]:
        portfolio, profile = self.resolve(key)
        policy = request.policy()
        before = AccountingPolicy.from_config(profile.configuration).to_dict()
        if before == policy.to_dict():
            raise ValueError("Accounting policy is unchanged")
        entries, _ = load_entries(self.session, portfolio.id)
        state = LedgerState(policy=policy)
        for entry in entries:
            state.apply(entry)
        profile.configuration = {**profile.configuration, "accounting": policy.to_dict()}
        self._audit(
            "ACCOUNTING_POLICY_CHANGED",
            portfolio.id,
            actor,
            {
                "before": before,
                "after": policy.to_dict(),
                "reason": request.reason,
                "replay_scope": "Full effective ledger; existing valuation runs retained",
            },
        )
        self.session.flush()
        return self.metadata(portfolio.id)

    def _audit(
        self, action: str, portfolio_id: str, actor: str | None, details: dict[str, Any]
    ) -> None:
        self.session.add(
            models.AuditLog(
                action=action,
                resource_type="portfolio",
                resource_id=portfolio_id,
                actor_user_id=actor,
                correlation_id=str(uuid4()),
                metadata_json=details,
            )
        )
        self.session.flush()
