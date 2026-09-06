import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
for directory in (ROOT, ROOT / "services" / "api"):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))


@pytest.fixture
def ledger_session() -> Iterator[Session]:
    from datetime import UTC, date, datetime
    from decimal import Decimal

    from app import models
    from sqlalchemy import create_engine, event
    from sqlalchemy.pool import StaticPool

    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def enforce_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    models.Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False, autoflush=False) as session:
        portfolio = models.Portfolio(
            id="book",
            name="Accounting test book",
            base_currency="SGD",
            reference_capital=Decimal("10000"),
            is_default=False,
        )
        session.add(portfolio)
        session.flush()
        session.add(
            models.PortfolioProfile(
                portfolio_id="book",
                code="TEST_BOOK",
                is_demo=False,
                configuration={"benchmark": "SPY", "allow_short": True},
            )
        )
        session.add(
            models.PortfolioAccount(
                id="account",
                portfolio_id="book",
                account_type="INTERNAL",
                display_name="Test account",
            )
        )
        for identifier, currency in (("AAA", "SGD"), ("BBB", "SGD"), ("SPY", "USD")):
            session.add(
                models.Instrument(
                    id=identifier,
                    symbol=identifier,
                    name=f"Test {identifier}",
                    currency=currency,
                    country="Test",
                    asset_class="Equity",
                    security_type="Common Stock",
                    sector="Test",
                )
            )
        session.flush()
        for day in (5, 6, 7, 8, 9):
            stamp = datetime(2026, 1, day, 20, tzinfo=UTC)
            for identifier, currency in (("AAA", "SGD"), ("BBB", "SGD"), ("SPY", "USD")):
                session.add(
                    models.MarketObservation(
                        instrument_id=identifier,
                        timestamp=stamp,
                        price=Decimal("120"),
                        currency=currency,
                        source="TEST",
                        source_category="FILE",
                        data_state="FILE IMPORT",
                        fields={},
                    )
                )
            session.add(
                models.FxObservation(
                    base_currency="USD",
                    quote_currency="SGD",
                    timestamp=stamp,
                    rate=Decimal("1.3"),
                    source="TEST",
                    source_category="FILE",
                    data_state="FILE IMPORT",
                )
            )
        session.add(
            models.PortfolioTransaction(
                id="deposit",
                portfolio_id="book",
                account_id="account",
                transaction_type="DEPOSIT",
                trade_date=date(2026, 1, 5),
                settle_date=date(2026, 1, 5),
                quantity=0,
                price=0,
                currency="SGD",
                fx_rate_to_base=1,
                fee=0,
                source="TEST",
                quality="INTERNAL LEDGER",
            )
        )
        session.flush()
        session.add(
            models.TransactionDetail(
                transaction_id="deposit", gross_amount=Decimal("10000"), base_value=Decimal("10000")
            )
        )
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def session_token(ledger_session: Session) -> str:
    import secrets
    from datetime import UTC, datetime, timedelta
    from app import models
    from app.auth_sessions import token_digest

    token = secrets.token_urlsafe(32)
    user = models.User(email="ledger-tests@example.test", password_hash="test-session-only", role="ADMIN")
    ledger_session.add(user)
    ledger_session.flush()
    ledger_session.add(models.UserSession(user_id=user.id, session_hash=token_digest(token), expires_at=datetime.now(UTC) + timedelta(hours=1)))
    ledger_session.commit()
    return token


@pytest.fixture
def client(ledger_session: Session, session_token: str) -> Iterator[TestClient]:
    from app.database import get_session
    from app.portfolio_resource_api import router
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    def session_override() -> Iterator[Session]:
        yield ledger_session

    app.dependency_overrides[get_session] = session_override
    with TestClient(app) as test_client:
        test_client.cookies.set("knk_session", session_token)
        yield test_client
