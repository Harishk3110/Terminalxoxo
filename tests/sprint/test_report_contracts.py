import pytest
from app import models, terminal_api
from app.services import ReportService


def capture(monkeypatch):
    monkeypatch.setattr(
        ReportService,
        "_write_workbook",
        lambda self, slug, sheets, **metadata: {"sheets": sheets, **metadata},
    )


def test_position_report_preserves_contract_multiplier_and_source_quality(
    monkeypatch, ledger_session
):
    capture(monkeypatch)
    monkeypatch.setattr(
        terminal_api,
        "portfolio_analytics",
        lambda session: {
            "positions": [
                {
                    "symbol": "OPTION",
                    "quantity": "2",
                    "market_price": "3",
                    "fx_rate": "1.3",
                    "contract_multiplier": "100",
                }
            ],
            "source": "FILE",
            "quality": "FILE IMPORT",
            "as_of": "2026-01-01",
            "risk": {},
            "performance": {},
            "warnings": [],
        },
    )
    result = terminal_api.terminal_report("portfolio", ledger_session)
    row = result["sheets"]["Positions"][1]
    assert row[4] == 100
    assert row[5].expression == "=B2*C2*D2*E2"
    assert row[5].cached_value == pytest.approx(780, abs=0.00000001)
    assert result["quality"] == "FILE IMPORT"


def test_run_export_preserves_missing_timestamp_and_heterogeneous_column_order(
    monkeypatch, ledger_session
):
    capture(monkeypatch)
    run = models.AnalysisRun(
        kind="wacc",
        name="Assumptions",
        status="SUCCEEDED",
        parameters={},
        history=[],
        result={
            "quality": "ESTIMATE",
            "contributions": [{"symbol": "A", "value": 1}, {"value": 2, "other": 3}],
        },
    )
    ledger_session.add(run)
    ledger_session.commit()
    result = terminal_api.export_run(run.id, ledger_session)
    assert ["Data as of", None] in result["sheets"]["Run"]
    assert result["sheets"]["Results"] == [
        ["symbol", "value", "other"],
        ["A", 1, None],
        [None, 2, 3],
    ]
    assert result["quality"] == "ESTIMATE"
