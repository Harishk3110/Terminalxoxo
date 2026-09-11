"""One request must not reload the full price store for each factor security."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app import models
from app.terminal_analytics import factor_analysis, quotes
from sqlalchemy import event
from sqlalchemy.orm import Session


@pytest.mark.parametrize("view", ["quotes", "factors"])
def test_market_history_is_loaded_once_per_request(ledger_session: Session, view: str) -> None:
    session = ledger_session
    today = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    symbols = [f"FACTOR{i}" for i in range(6)]
    for index, symbol in enumerate(symbols):
        session.add(
            models.Instrument(
                id=symbol,
                symbol=symbol,
                name=symbol,
                currency="SGD",
                country="Test",
                asset_class="Equity",
                security_type="Common Stock",
                sector="Fixture",
            )
        )
        session.flush()
        for day in range(80):
            close = Decimal(100 + index * day + (day % (index + 2)))
            session.add(
                models.PriceBar(
                    instrument_id=symbol,
                    timestamp=today - timedelta(days=80 - day),
                    interval="1d",
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=None,
                    currency="SGD",
                    provider="Legacy factor fixture",
                    quality="DEMO DATA",
                )
            )
        session.add(
            models.LatestQuote(
                instrument_id=symbol,
                price=close,
                currency="SGD",
                as_of=today,
                provider="Managed factor fixture",
                quality="DEMO DATA",
            )
        )
        session.add(
            models.MarketObservation(
                instrument_id=symbol,
                timestamp=today,
                price=close,
                currency="SGD",
                source="Managed factor fixture",
                source_category="DEMO",
                data_state="DEMO",
                fields={},
            )
        )
    session.flush()
    reads: list[str] = []

    def observe(*args: object) -> None:
        statement = args[2]
        if isinstance(statement, str) and "from price_bars" in statement.lower():
            reads.append(statement)

    bind = session.get_bind()
    event.listen(bind, "before_cursor_execute", observe)
    try:
        if view == "quotes":
            result = quotes(session)
            assert {row["symbol"] for row in result} == set(symbols)
            assert all(row["source"] == "Managed factor fixture" for row in result)
        else:
            data = factor_analysis(session, 21, "VOLATILITY")
            assert {row["symbol"] for row in data["items"]} == set(symbols)
            assert data["lookback"] == 21
            assert data["diagnostics"]["state"] == "CALCULATED"
        assert len(reads) == 1
    finally:
        event.remove(bind, "before_cursor_execute", observe)
