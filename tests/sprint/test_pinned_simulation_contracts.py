"""Pinned simulation inputs preserve evidence and reject unavailable observations."""

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from app import models
from app.backtest_inputs import pin_backtest_inputs
from app.config import get_settings
from app.monte_carlo import MonteCarloSettings, monte_carlo_result, pin_monte_carlo
from app.performance_domain.contracts import PerformanceSettings
from app.portfolio_performance import PortfolioPerformanceService
from pydantic import JsonValue, TypeAdapter
from sqlalchemy.orm import Session

JSON_OBJECT = TypeAdapter(dict[str, JsonValue])
JSON_ROWS = TypeAdapter(list[dict[str, JsonValue]])
FLOATS = TypeAdapter(list[float])


def saved_backtest(session: Session) -> models.AnalysisRun:
    row = models.AnalysisRun(
        kind="backtest",
        name="Pinned contract fixture",
        status="SUCCEEDED",
        parameters={},
        history=[],
        result={
            "equity_curve": [
                {"date": day.date().isoformat(), "equity": float(100000 * 1.001**i)}
                for i, day in enumerate(pd.bdate_range("2025-01-01", periods=61))
            ],
            "source": "FILE fixture",
            "quality": "FILE IMPORT",
            "as_of": "2025-03-26",
        },
    )
    session.add(row)
    session.flush()
    return row


def test_saved_curve_is_pinned_without_rewriting_evidence(ledger_session: Session) -> None:
    run = saved_backtest(ledger_session)
    parameters: dict[str, JsonValue] = {
        "backtest_run_id": run.id,
        "settings": {"paths": 100, "horizon": 10},
    }
    before = deepcopy(parameters)
    saved_result = deepcopy(run.result)
    pinned = pin_monte_carlo(ledger_session, parameters)
    result = monte_carlo_result(pinned)
    assert parameters == before
    assert run.result == saved_result
    assert result["observations"] == 60
    assert result["source"] == "FILE fixture"
    assert result["quality"] == "FILE IMPORT"
    assert result["as_of"] == "2025-03-26"
    assert result["inputs"] == pinned["_evidence"]
    assert result["cost_basis"] == "Saved strategy net curve"
    assert result == monte_carlo_result(pinned)


@pytest.mark.parametrize("case", ["missing", "duplicate", "reversed", "malformed", "null"])
def test_invalid_saved_curve_is_not_repaired(ledger_session: Session, case: str) -> None:
    run = saved_backtest(ledger_session)
    result = JSON_OBJECT.validate_python(run.result, strict=True)
    curve = JSON_ROWS.validate_python(result["equity_curve"], strict=True)
    if case == "missing":
        curve = [{"date": row["date"]} for row in curve]
    elif case == "duplicate":
        curve[1]["date"] = curve[0]["date"]
    elif case == "reversed":
        curve.reverse()
    elif case == "malformed":
        curve[0]["date"] = "not-a-date"
    else:
        curve[10]["equity"] = None
    run.result = {**result, "equity_curve": [row for row in curve]}
    before = deepcopy(run.result)
    with pytest.raises(ValueError):
        pin_monte_carlo(ledger_session, {"backtest_run_id": run.id})
    assert run.result == before


@pytest.mark.parametrize("state", ["QUEUED", "RUNNING", "FAILED", "CANCELLED"])
def test_only_completed_backtests_are_eligible(ledger_session: Session, state: str) -> None:
    run = saved_backtest(ledger_session)
    run.status = state
    with pytest.raises(ValueError, match="completed backtest"):
        pin_monte_carlo(ledger_session, {"backtest_run_id": run.id})


@pytest.mark.parametrize("invalid", [True, "0.01", None, {}, []])
def test_worker_rejects_malformed_pinned_returns(invalid: JsonValue) -> None:
    parameters: dict[str, JsonValue] = {
        "_returns": [invalid] * 60,
        "settings": {"paths": 100, "horizon": 10},
        "_evidence": {"quality": "FILE IMPORT"},
    }
    with pytest.raises(ValueError):
        monte_carlo_result(parameters)


@pytest.mark.parametrize("invalid", [None, True, "NaN"])
def test_portfolio_missing_returns_are_not_zero_filled(
    ledger_session: Session, monkeypatch: pytest.MonkeyPatch, invalid: JsonValue
) -> None:
    def report(
        self: PortfolioPerformanceService,
        key: str,
        settings: PerformanceSettings,
        valuation_run_id: str | None = None,
    ) -> dict[str, JsonValue]:
        return {
            "summary": {"volatility": {"state": "AVAILABLE"}},
            "series": [
                {"end": day.date().isoformat(), "value": invalid if i == 3 else 0.0}
                for i, day in enumerate(pd.bdate_range("2025-01-01", periods=60))
            ],
            "valuation_run_id": "saved-nav",
            "source_quality": "FILE IMPORT",
        }

    monkeypatch.setattr(PortfolioPerformanceService, "calculate", report)
    with pytest.raises(ValueError):
        pin_monte_carlo(ledger_session, {})


def test_portfolio_true_zero_returns_retain_pinned_nav(
    ledger_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    def report(
        self: PortfolioPerformanceService,
        key: str,
        settings: PerformanceSettings,
        valuation_run_id: str | None = None,
    ) -> dict[str, JsonValue]:
        assert key == "TEST_BOOK"
        assert valuation_run_id == "saved-nav"
        return {
            "summary": {"volatility": {"state": "AVAILABLE"}},
            "series": [
                {"end": day.date().isoformat(), "value": "0"}
                for day in pd.bdate_range("2025-01-01", periods=60)
            ],
            "valuation_run_id": "saved-nav",
            "source_quality": "FILE IMPORT",
        }

    monkeypatch.setattr(PortfolioPerformanceService, "calculate", report)
    pinned = pin_monte_carlo(
        ledger_session, {"portfolio": "TEST_BOOK", "valuation_run_id": "saved-nav"}
    )
    assert FLOATS.validate_python(pinned["_returns"], strict=True) == [0.0] * 60
    evidence = JSON_OBJECT.validate_python(pinned["_evidence"], strict=True)
    assert evidence["valuation_run_id"] == "saved-nav"
    assert evidence["quality"] == "FILE IMPORT"


@pytest.mark.parametrize("symbols", [["SPY", "SPY"], ["SPY", 1], {"SPY": 1}, ["SPY"] * 13])
def test_invalid_symbol_selection_cannot_pin_inputs(
    ledger_session: Session, symbols: JsonValue
) -> None:
    with pytest.raises(ValueError, match="unique list"):
        pin_backtest_inputs(ledger_session, {"symbols": symbols})


@pytest.mark.parametrize("base", [None, 123, "US", "US1", "USDD"])
def test_invalid_base_currency_is_rejected(ledger_session: Session, base: JsonValue) -> None:
    with pytest.raises(ValueError, match="base currency"):
        pin_backtest_inputs(ledger_session, {"symbols": ["SPY"], "base_currency": base})


def test_identity_fx_preserves_exact_pinned_dataset(
    ledger_session: Session, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(get_settings(), "object_storage_local_dir", str(tmp_path))
    for offset in range(3):
        ledger_session.add(
            models.PriceBar(
                instrument_id="SPY",
                timestamp=pd.Timestamp(date(2025, 1, 1) + timedelta(days=offset)).to_pydatetime(),
                interval="1d",
                open=100,
                high=101,
                low=99,
                close=100,
                currency="USD",
                provider="DemoProvider",
                quality="DEMO DATA",
            )
        )
    ledger_session.flush()
    parameters: dict[str, JsonValue] = {
        "symbols": ["SPY"],
        "source_mode": "DEMO_RESEARCH",
        "base_currency": "usd",
    }
    before = deepcopy(parameters)
    result = pin_backtest_inputs(ledger_session, parameters)
    assert parameters == before
    assert result["base_currency"] == "USD"
    datasets = JSON_OBJECT.validate_python(result["_datasets"], strict=True)
    dataset = JSON_OBJECT.validate_python(datasets["SPY"], strict=True)
    assert result["dataset_version_id"] == dataset["dataset_version_id"]
    assert result["dataset_id"] == dataset["dataset_id"]
    assert dataset["quality"] == "DEMO DATA"
    fixings = JSON_OBJECT.validate_python(result["_fx"], strict=True)
    daily = JSON_OBJECT.validate_python(fixings["SPY"], strict=True)
    assert len(daily) == 3
    for day, value in daily.items():
        fixing = JSON_OBJECT.validate_python(value, strict=True)
        assert fixing["rate"] == "1"
        source = JSON_OBJECT.validate_python(fixing["provenance"], strict=True)
        assert source["source"] == "IDENTITY"
        assert source["data_state"] == "CALCULATED"
        observed = source["as_of"]
        assert isinstance(observed, str)
        assert observed < day


def test_normal_loss_floor_is_disclosed_without_nonfinite_results() -> None:
    from app.monte_carlo import monte_carlo

    result = monte_carlo(
        np.tile([-0.99, 5.0], 50),
        MonteCarloSettings(method="NORMAL", paths=100, horizon=5),
    )
    assert all(np.isfinite(value) for value in result["metrics"].values())
    assert any("Limited-liability floor" in warning for warning in result["warnings"])
    assert sum(row["count"] for row in result["terminal_distribution"]) == 100
