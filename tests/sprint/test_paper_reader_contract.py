"""Exercise the paper reader with SDK-shaped records and no broker connection."""

import asyncio
import importlib.util
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from ib_async import AccountValue, Contract, ExecutionFilter, Fill, PortfolioItem, StartupFetch


@pytest.fixture
def reader(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    root = Path(__file__).resolve().parents[2] / "services/local-agent"
    monkeypatch.syspath_prepend(str(root))
    spec = importlib.util.spec_from_file_location(
        "paper_reader_contract", root / "broker_reader.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def observed(reader: ModuleType, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    calls: dict[str, object] = {}

    class FakeIB:
        def __init__(self) -> None:
            calls["created"] = True

        async def connectAsync(self, host: str, port: int, **kwargs: object) -> None:
            calls.update(kwargs)

        def managedAccounts(self) -> list[str]:
            return ["DU_TEST_ONLY"]

        async def accountSummaryAsync(self, account: str) -> list[AccountValue]:
            return [AccountValue(account, "NetLiquidation", "100000", "SGD", "")]

        def accountValues(self, account: str) -> list[AccountValue]:
            return [AccountValue(account, "CashBalance", "0", "SGD", "")]

        def portfolio(self, account: str) -> list[PortfolioItem]:
            return []

        async def reqExecutionsAsync(self, selection: ExecutionFilter) -> list[Fill]:
            return []

        def disconnect(self) -> None:
            calls["disconnected"] = True

    monkeypatch.setattr(reader, "IB", FakeIB)
    return calls


def settings(**overrides: object) -> SimpleNamespace:
    return SimpleNamespace(
        **{
            "host": "127.0.0.1",
            "port": 7497,
            "account": "DU_TEST_ONLY",
            "currency": "SGD",
            "client_id": 3110,
            **overrides,
        }
    )


@pytest.mark.parametrize("client_id", [0, -1, 2147483648])
def test_special_or_invalid_client_ids_never_reach_the_sdk(
    reader: ModuleType,
    observed: dict[str, object],
    client_id: int,
) -> None:
    with pytest.raises(ValueError, match="client"):
        asyncio.run(reader.read_snapshot(settings(client_id=client_id)))
    assert observed == {}


def test_explicit_readonly_fetch_preserves_actual_zero_cash(
    reader: ModuleType,
    observed: dict[str, object],
) -> None:
    result = asyncio.run(reader.read_snapshot(settings()))
    assert result["cash"] == [{"currency": "SGD", "amount": "0"}]
    assert result["nav"] == "100000"
    assert observed["readonly"] is True
    assert observed["fetchFields"] == (
        StartupFetch.POSITIONS | StartupFetch.ACCOUNT_UPDATES | StartupFetch.EXECUTIONS
    )
    assert observed["disconnected"] is True


@pytest.mark.parametrize("security_type", ["OPT", "FUT"])
def test_derivative_multiplier_is_never_invented(
    reader: ModuleType,
    observed: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
    security_type: str,
) -> None:
    contract = Contract(
        secType=security_type, symbol="TEST", localSymbol="TEST CONTRACT", currency="SGD"
    )
    position = PortfolioItem(contract, 2, 5, 1000, 500, 0, 0, "DU_TEST_ONLY")
    monkeypatch.setattr(reader.IB, "portfolio", lambda self, account: [position])
    with pytest.raises(ValueError, match="multiplier"):
        asyncio.run(reader.read_snapshot(settings()))
    assert observed["disconnected"] is True


def test_option_cost_is_per_unit_and_unknown_mark_stays_unavailable(
    reader: ModuleType,
    observed: dict[str, object],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    contract = Contract(
        secType="OPT", symbol="TEST", localSymbol="TEST CONTRACT", currency="SGD", multiplier="100"
    )
    position = PortfolioItem(contract, -2, float("nan"), float("nan"), 500, 0, 0, "DU_TEST_ONLY")
    monkeypatch.setattr(reader.IB, "portfolio", lambda self, account: [position])
    result = asyncio.run(reader.read_snapshot(settings()))
    assert result["positions"] == [
        {
            "symbol": "TEST CONTRACT",
            "currency": "SGD",
            "quantity": "-2",
            "average_cost": "5",
            "multiplier": "100",
            "market_price": None,
        }
    ]
    assert observed["disconnected"] is True
