from decimal import Decimal

import pytest
from app import models
from app.risk_limits import LimitRequest, RiskLimitService
from pydantic import JsonValue
from sqlalchemy import func, select
from sqlalchemy.orm import Session


def data(value: float | None) -> dict[str, JsonValue]:
    return {
        "portfolio": {"id": "book", "nav": 10000},
        "risk": {"gross_exposure": value},
        "valuation_run_id": "test-run",
        "source": "TEST",
        "as_of": "2026-01-09",
    }


def test_breach_persists_once_missing_is_not_clear_and_recovery_is_audited(
    ledger_session: Session,
) -> None:
    service = RiskLimitService(ledger_session)
    service.configure(
        "book",
        LimitRequest(
            metric="gross_exposure", threshold=Decimal(".5"), reason="Review exposure limit"
        ),
        None,
    )
    first = service.evaluate(data(0.7))
    assert first[0]["state"] == "BREACH"
    assert first[0]["first_breach"] and first[0]["alert_id"]
    service.evaluate(data(0.7))
    assert ledger_session.scalar(select(func.count(models.RiskBreach.id))) == 1
    assert ledger_session.scalar(select(func.count(models.Alert.id))) == 1
    assert (
        ledger_session.scalar(
            select(func.count(models.AuditLog.id)).where(
                models.AuditLog.action == "RISK_BREACH_STATE_CHANGED"
            )
        )
        == 1
    )
    service.evaluate(data(None))
    breach = ledger_session.get(models.RiskBreach, first[0]["breach_id"])
    alert = ledger_session.get(models.Alert, first[0]["alert_id"])
    assert breach is not None and breach.state == "UNDETERMINED"
    assert alert is not None and alert.state == "OPEN"
    service.evaluate(data(0.2))
    breach = ledger_session.get(models.RiskBreach, first[0]["breach_id"])
    alert = ledger_session.get(models.Alert, first[0]["alert_id"])
    assert breach is not None and breach.state == "RESOLVED"
    assert alert is not None and alert.state == "RESOLVED"
    service.evaluate(data(0.9))
    assert ledger_session.scalar(select(func.count(models.Alert.id))) == 2
    assert ledger_session.scalar(select(func.count(models.RiskBreach.id))) == 1


def test_loss_limits_compare_positive_loss_magnitudes(ledger_session: Session) -> None:
    service = RiskLimitService(ledger_session)
    service.configure(
        "book",
        LimitRequest(metric="var_loss_95", threshold=Decimal("100"), reason="Loss budget review"),
        None,
    )
    result = service.evaluate({**data(0), "risk": {"var_95": -150}})
    assert result[0]["state"] == "BREACH"
    assert result[0]["value"] is not None
    assert Decimal(result[0]["value"]) == 150


def test_disabling_limit_preserves_evidence_and_configuration_requires_valid_metric(
    ledger_session: Session,
) -> None:
    service = RiskLimitService(ledger_session)
    request = LimitRequest(
        metric="gross_exposure", threshold=Decimal(".5"), reason="Review exposure limit"
    )
    row = service.configure("book", request, None)
    first = service.evaluate(data(0.7))[0]
    service.configure("book", request.model_copy(update={"enabled": False}), None, row["id"])
    assert service.evaluate(data(0.7))[0]["state"] == "DISABLED"
    breach = ledger_session.get(models.RiskBreach, first["breach_id"])
    assert breach is not None and breach.state == "RESOLVED"
    with pytest.raises(ValueError):
        LimitRequest(metric="invented", threshold=Decimal(1), reason="Review invalid metric")
    with pytest.raises(ValueError, match="does not belong"):
        service.configure("book", request, None, "another-book-limit")
