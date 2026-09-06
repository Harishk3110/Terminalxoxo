"""Portfolio resources; mutations are internal records, never broker instructions."""

from collections.abc import Generator
from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import get_session
from .ledger_contracts import (
    AccountingPolicyRequest,
    AmendmentRequest,
    PortfolioCreateRequest,
    RevisionRequest,
)
from .ledger_revisions import PortfolioTransactionService, RevisionConflict
from .portfolio_api import LedgerRequest, ResetRequest, identity
from .portfolio_balances import BalanceAdjustmentRequest, PortfolioBalanceService
from .portfolio_domain.postings import PostingCategory
from .portfolio_operations import PortfolioLedgerService
from .portfolio_resources import PortfolioNotFound, PortfolioResourceService
from .portfolio_seed import reset_main_demo

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolio-resources"])


def resource_session(
    request: Request, session: Annotated[Session, Depends(get_session)]
) -> Generator[Session, None, None]:
    identity(request, session)
    try:
        yield session
        session.commit()
    except PortfolioNotFound as exc:
        session.rollback()
        raise HTTPException(404, str(exc)) from exc
    except (IntegrityError, RevisionConflict) as exc:
        session.rollback()
        raise HTTPException(
            409,
            str(exc)
            if isinstance(exc, RevisionConflict)
            else "Record conflicts with an existing identifier or version",
        ) from exc
    except ValueError as exc:
        session.rollback()
        raise HTTPException(422, str(exc)) from exc


Database = Annotated[Session, Depends(resource_session)]


@router.get("")
def list_portfolios(session: Database) -> dict[str, Any]:
    return {"items": PortfolioResourceService(session).list_portfolios()}


@router.post("", status_code=201)
def create_portfolio(
    payload: PortfolioCreateRequest, request: Request, session: Database
) -> dict[str, Any]:
    return PortfolioResourceService(session).create(payload, identity(request, session))


@router.get("/creation-options")
def creation_options(session: Database) -> dict[str, Any]:
    return PortfolioResourceService(session).creation_options()


@router.get("/{portfolio_id}")
def portfolio(portfolio_id: str, session: Database) -> dict[str, Any]:
    return PortfolioResourceService(session).metadata(portfolio_id)


@router.get("/{portfolio_id}/summary")
def summary(portfolio_id: str, session: Database, end: date | None = None) -> dict[str, Any]:
    return PortfolioResourceService(session).summary(portfolio_id, end)


@router.get("/{portfolio_id}/positions")
def positions(portfolio_id: str, session: Database, end: date | None = None) -> dict[str, Any]:
    data = PortfolioResourceService(session).summary(portfolio_id, end)
    return {"items": data["positions"], "valuation_run_id": data["valuation_run_id"]}


@router.get("/{portfolio_id}/positions/{position_id}")
def position(
    portfolio_id: str,
    position_id: str,
    session: Database,
    end: date | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return PortfolioResourceService(session).position(portfolio_id, position_id, end, run_id)


@router.get("/{portfolio_id}/transactions")
def transactions(portfolio_id: str, session: Database) -> dict[str, Any]:
    return {"items": PortfolioResourceService(session).transactions(portfolio_id)}


@router.get("/{portfolio_id}/entry-options")
def entry_options(portfolio_id: str, session: Database) -> dict[str, Any]:
    return PortfolioResourceService(session).entry_options(portfolio_id)


@router.post("/{portfolio_id}/transactions", status_code=201)
def add_transaction(
    portfolio_id: str, payload: LedgerRequest, request: Request, session: Database
) -> dict[str, Any]:
    portfolio, _ = PortfolioResourceService(session).resolve(portfolio_id)
    return dict(
        PortfolioLedgerService(session).add(
            payload.model_dump(mode="json", exclude_none=True),
            portfolio.id,
            actor=identity(request, session),
        )
    )


@router.get("/{portfolio_id}/transactions/{transaction_id}")
def transaction(portfolio_id: str, transaction_id: str, session: Database) -> dict[str, Any]:
    resources = PortfolioResourceService(session)
    portfolio, _ = resources.resolve(portfolio_id)
    return {
        **resources.transaction(portfolio.id, transaction_id),
        "revisions": PortfolioTransactionService(session).history(portfolio.id, transaction_id),
    }


@router.put("/{portfolio_id}/transactions/{transaction_id}")
def amend_transaction(
    portfolio_id: str,
    transaction_id: str,
    payload: AmendmentRequest,
    request: Request,
    session: Database,
) -> dict[str, Any]:
    portfolio, _ = PortfolioResourceService(session).resolve(portfolio_id)
    return PortfolioTransactionService(session).revise(
        portfolio.id, transaction_id, payload, actor=identity(request, session)
    )


@router.delete("/{portfolio_id}/transactions/{transaction_id}")
def void_transaction(
    portfolio_id: str,
    transaction_id: str,
    payload: RevisionRequest,
    request: Request,
    session: Database,
) -> dict[str, Any]:
    portfolio, _ = PortfolioResourceService(session).resolve(portfolio_id)
    return PortfolioTransactionService(session).revise(
        portfolio.id, transaction_id, payload, actor=identity(request, session)
    )


@router.put("/{portfolio_id}/accounting-policy")
def accounting_policy(
    portfolio_id: str, payload: AccountingPolicyRequest, request: Request, session: Database
) -> dict[str, Any]:
    return PortfolioResourceService(session).change_policy(
        portfolio_id, payload, identity(request, session)
    )


@router.get("/{portfolio_id}/cash")
def cash(portfolio_id: str, session: Database, end: date | None = None) -> dict[str, Any]:
    data = PortfolioResourceService(session).summary(portfolio_id, end)
    return {
        "items": data["cash"],
        "portfolio": data["portfolio"],
        "valuation_run_id": data["valuation_run_id"],
    }


@router.get("/{portfolio_id}/nav")
def nav(
    portfolio_id: str, session: Database, end: date | None = None, run_id: str | None = None
) -> dict[str, Any]:
    data = PortfolioResourceService(session).valuation_snapshot(portfolio_id, run_id, end)
    return {
        "portfolio": data["portfolio"],
        "curve": data["curve"],
        "reconciliation": data["reconciliation"],
        "balance_sheet": data.get("balance_sheet"),
        "state": data["balance_sheet"]["state"] if "balance_sheet" in data else "LEGACY_SNAPSHOT",
        "valuation_run_id": data.get("valuation_run_id", run_id),
        "valuation_date": data["curve"][-1]["date"],
        "calculation_version": data["calculation_version"],
        "quality": data["quality"],
        "calculated_at": data["calculated_at"],
    }


@router.get("/{portfolio_id}/accounting")
def accounting(
    portfolio_id: str,
    session: Database,
    run_id: str | None = None,
    category: PostingCategory | None = None,
) -> dict[str, Any]:
    return PortfolioResourceService(session).accounting(portfolio_id, run_id, category)


@router.get("/{portfolio_id}/balances")
def balances(portfolio_id: str, session: Database) -> dict[str, Any]:
    portfolio, _ = PortfolioResourceService(session).resolve(portfolio_id)
    return {"items": PortfolioBalanceService(session).list(portfolio.id)}


@router.post("/{portfolio_id}/balances", status_code=201)
def add_balance(
    portfolio_id: str,
    payload: BalanceAdjustmentRequest,
    request: Request,
    session: Database,
) -> dict[str, Any]:
    portfolio, _ = PortfolioResourceService(session).resolve(portfolio_id)
    return PortfolioBalanceService(session).add(portfolio.id, payload, identity(request, session))


@router.post("/{portfolio_id}/value")
@router.post("/{portfolio_id}/recalculate")
def recalculate(
    portfolio_id: str, request: Request, session: Database, end: date | None = None
) -> dict[str, Any]:
    return PortfolioResourceService(session).recalculate(
        portfolio_id, end, identity(request, session)
    )


@router.get("/{portfolio_id}/performance")
def performance(portfolio_id: str, session: Database, end: date | None = None) -> dict[str, Any]:
    data = PortfolioResourceService(session).summary(portfolio_id, end)
    return {
        "metrics": data["performance"],
        "metadata": data["metric_metadata"],
        "monthly": data["monthly"],
        "warnings": data["warnings"],
    }


@router.get("/{portfolio_id}/attribution")
def attribution(portfolio_id: str, session: Database, end: date | None = None) -> dict[str, Any]:
    data = PortfolioResourceService(session).summary(portfolio_id, end)
    return {
        "items": data["attribution"],
        "reconciliation": data["reconciliation"],
        "valuation_run_id": data["valuation_run_id"],
    }


@router.get("/{portfolio_id}/exposures")
def exposures(
    portfolio_id: str,
    session: Database,
    end: date | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return PortfolioResourceService(session).exposures(portfolio_id, run_id, end)


@router.post("/{portfolio_id}/reset-demo")
def reset_demo(
    portfolio_id: str, payload: ResetRequest, request: Request, session: Database
) -> dict[str, Any]:
    resources = PortfolioResourceService(session)
    _, profile = resources.resolve(portfolio_id)
    actor = identity(request, session, admin=True)
    if (
        profile.code != "KNK_MAIN"
        or not profile.is_demo
        or payload.confirmation != "RESET KNK_MAIN DEMO"
    ):
        raise ValueError("Only KNK_MAIN demo can be reset with explicit confirmation")
    replacement = reset_main_demo(session, actor)
    return resources.metadata(replacement.id)
