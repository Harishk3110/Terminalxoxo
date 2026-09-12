"""Risk availability, configuration validation and legacy audit evidence."""

from datetime import date
from decimal import Decimal
from typing import Literal, NoReturn

import pytest
from app import models
from app.portfolio_valuation import PortfolioValuationService
from app.risk_limits import METRICS, LimitRequest, RiskLimitService, metric_value
from pydantic import JsonValue
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_risk_limits import data


@pytest.mark.parametrize("metric", sorted(METRICS))
@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("0", Decimal(0)),
        ("0.125000000000000001", Decimal("0.125000000000000001")),
        (-0.25, Decimal("-0.25")),
        (Decimal("0.123456789123456789"), Decimal("0.123456789123456789")),
        ("NaN", None),
        ("Infinity", None),
        ("-Infinity", None),
    ],
)
def test_risk_metric_precision_sign_and_availability(
    metric: str,
    value: Decimal | float | str | None,
    expected: Decimal | None,
) -> None:
    sources = {
        "var_loss_95": "var_95",
        "cvar_loss_95": "cvar_95",
        "drawdown_loss": "current_drawdown",
    }
    result = metric_value(
        {"portfolio": {"nav": "10000"}, "risk": {sources.get(metric, metric): value}},
        metric,
    )
    assert result == (abs(expected) if expected is not None and metric in sources else expected)
    if expected is not None:
        assert isinstance(result, Decimal)


@pytest.mark.parametrize("nav", [None, 0, -1, "NaN", "Infinity", "-Infinity"])
def test_unavailable_or_nonpositive_nav_cannot_pass_a_limit(nav: JsonValue) -> None:
    assert metric_value({"portfolio": {"nav": nav}, "risk": {"beta": 1.2}}, "beta") is None


def test_missing_nav_or_metric_is_unavailable_not_zero() -> None:
    assert metric_value({}, "beta") is None
    assert metric_value({"portfolio": {"nav": "10000"}}, "beta") is None


@pytest.mark.parametrize("bad", [True, {}, [], "invalid"])
def test_malformed_metric_is_rejected(bad: JsonValue) -> None:
    with pytest.raises(ValueError):
        metric_value({"portfolio": {"nav": 10000}, "risk": {"beta": bad}}, "beta")


@pytest.mark.parametrize("bad", [None, True, 0, "one-limit-id", ["one", None], {}, ["one", 1]])
@pytest.mark.parametrize("operation", ["create", "update", "evaluate"])
def test_invalid_disabled_ids_reject_without_mutating_limits_or_breach_history(
    ledger_session: Session,
    bad: JsonValue,
    operation: Literal["create", "update", "evaluate"],
) -> None:
    service = RiskLimitService(ledger_session)
    request = LimitRequest(
        metric="gross_exposure", threshold=Decimal(".5"), reason="Review exposure limit"
    )
    existing = service.configure("book", request, None)
    profile = ledger_session.scalars(select(models.PortfolioProfile)).one()
    profile.configuration = {"disabled_risk_limit_ids": bad, "preserved": "source setting"}
    ledger_session.flush()
    before = ledger_session.scalar(select(func.count(models.AuditLog.id)))
    changed = LimitRequest(metric="beta", threshold=Decimal(".8"), reason="Review exposure limit")
    with pytest.raises(ValueError):
        if operation == "evaluate":
            service.evaluate(data(0.7))
        else:
            service.configure(
                "book", changed, None, existing["id"] if operation == "update" else None
            )
    limit = ledger_session.get(models.RiskLimit, existing["id"])
    assert limit is not None
    assert limit.metric == "gross_exposure" and limit.threshold == Decimal(".5")
    assert ledger_session.scalar(select(func.count(models.RiskLimit.id))) == 1
    assert ledger_session.scalar(select(func.count(models.RiskBreach.id))) == 0
    assert ledger_session.scalar(select(func.count(models.Alert.id))) == 0
    assert ledger_session.scalar(select(func.count(models.AuditLog.id))) == before
    assert profile.configuration == {"disabled_risk_limit_ids": bad, "preserved": "source setting"}


@pytest.mark.parametrize("bad", [None, True, 0, "one-limit-id", ["one", None], {}, ["one", 1]])
def test_valuation_rejects_invalid_disabled_ids_before_ledger_replay(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    bad: JsonValue,
) -> None:
    profile = ledger_session.scalars(select(models.PortfolioProfile)).one()
    profile.configuration = {"disabled_risk_limit_ids": bad}
    ledger_session.flush()

    def unexpected(_session: Session, _portfolio_id: str) -> NoReturn:
        pytest.fail("Malformed risk configuration must not load or replay the ledger")

    monkeypatch.setattr("app.portfolio_valuation.load_entries", unexpected)
    with pytest.raises(ValueError):
        PortfolioValuationService(ledger_session).latest(
            "book",
            force=True,
            end=date(2026, 1, 9),
            commit=False,
        )
    assert ledger_session.scalar(select(func.count(models.PortfolioValuationRun.id))) == 0
    assert ledger_session.scalar(select(func.count(models.NavSnapshot.id))) == 0


@pytest.mark.parametrize("metadata", [None, {}, {"reason": "Historical review"}])
def test_monitor_preserves_legacy_audit_rows_without_metadata(
    ledger_session: Session,
    monkeypatch: pytest.MonkeyPatch,
    metadata: dict[str, JsonValue] | None,
) -> None:
    service = RiskLimitService(ledger_session)
    service.configure(
        "book",
        LimitRequest(
            metric="gross_exposure", threshold=Decimal(".5"), reason="Review exposure limit"
        ),
        None,
    )
    breach = service.evaluate(data(0.7))[0]
    assert breach["breach_id"] is not None
    legacy = models.AuditLog(
        action="LEGACY_RISK_REVIEW",
        correlation_id="risk-legacy-fixture",
        resource_type="risk_breach",
        resource_id=breach["breach_id"],
        metadata_json=metadata,
    )
    ledger_session.add(legacy)
    ledger_session.flush()

    def latest(
        _self: PortfolioValuationService,
        key: str | None = None,
        *,
        commit: bool = True,
    ) -> dict[str, JsonValue]:
        assert key == "book" and not commit
        return {**data(0.7), "quality": "TEST", "warnings": [], "risk_model": {"source": "TEST"}}

    monkeypatch.setattr(PortfolioValuationService, "latest", latest)
    result = service.monitor("book")
    record = next(row for row in result["timeline"] if row["id"] == legacy.id)
    assert record == {
        "id": legacy.id,
        "timestamp": legacy.created_at.isoformat(),
        "action": "LEGACY_RISK_REVIEW",
        **(metadata or {}),
    }
    assert result["risk"] == {"gross_exposure": 0.7}
    assert result["limits"][0]["state"] == "BREACH"
    assert result["model"] == {"source": "TEST"}
