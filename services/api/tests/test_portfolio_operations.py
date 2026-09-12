import hashlib
from pathlib import Path

import pytest
from app import models
from app.data_drop import DataDropService
from app.data_mapping import seed_profiles
from app.object_storage import ObjectStorage
from app.portfolio_operations import PortfolioLedgerService, TradeMonitorService
from app.portfolio_valuation import PortfolioValuationService
from sqlalchemy import select
from sqlalchemy.orm import Session
from test_portfolio_accounting import accounting_session as accounting_session


@pytest.fixture
def drop(
    accounting_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> DataDropService:
    original = ObjectStorage.__init__

    def initialize(self: ObjectStorage) -> None:
        original(self)
        self.local_root = tmp_path
        self._s3 = None

    monkeypatch.setattr(ObjectStorage, "__init__", initialize)
    seed_profiles(accounting_session)
    accounting_session.commit()
    return DataDropService(accounting_session)


def profile(session: Session, code: str = "KOYFIN_PRICE_HISTORY") -> models.MappingProfile:
    selected = session.scalar(
        select(models.MappingProfile).where(models.MappingProfile.code == code)
    )
    assert selected is not None
    return selected


@pytest.mark.parametrize(
    "filename,content",
    [
        ("invalid.json", b'[{"close":NaN}]'),
        ("invalid.jsonl", b'{"metadata":{"close":Infinity}}'),
        ("blank.csv", b",close\nAAA,12\n"),
    ],
)
def test_invalid_preview_is_quarantined_with_immutable_raw_bytes(
    drop: DataDropService, accounting_session: Session, filename: str, content: bytes
) -> None:
    received = drop.receive(filename, content)
    assert received["state"] == "QUARANTINED"
    assert received["validation"]["valid"] is False
    assert received["validation"]["errors"]
    external = drop.get(received["id"])
    uploaded = accounting_session.get(models.UploadedFile, external.uploaded_file_id)
    assert uploaded is not None
    assert drop.storage.get_bytes(uploaded.object_key) == content
    assert uploaded.content_hash == hashlib.sha256(content).hexdigest()
    assert accounting_session.scalars(select(models.DatasetVersion)).all() == []
    with pytest.raises(ValueError, match="mapped"):
        drop.map_validate(received["id"], profile(accounting_session).id)


def test_file_preview_approval_immutable_and_duplicate(
    drop: DataDropService, accounting_session: Session
) -> None:
    raw = b"Date,Open,High,Low,Close,Volume\n2026-09-04,213,219,212,217,1000\n"
    uploaded = drop.receive("AAPL_2026-09-04_prices.csv", raw)
    assert uploaded["state"] == "MAPPING_REQUIRED"
    assert uploaded["hash"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match="approval"):
        drop.import_file(
            uploaded["id"], name="Apple prices", licence="Private exported file", approve=False
        )
    mapped = drop.map_validate(uploaded["id"], profile(accounting_session).id)
    assert mapped["state"] == "AWAITING_APPROVAL", mapped
    result = drop.import_file(
        uploaded["id"], name="Apple prices", licence="Private exported file", approve=True
    )
    assert result["state"] == "IMPORTED", result
    assert drop.raw_rows(drop.get(result["id"]))[0][0]["Close"] == "217"
    nav = PortfolioValuationService(accounting_session).latest(force=True)
    apple = next(p for p in nav["positions"] if p["symbol"] == "AAPL")
    assert apple["market_price"] == "217.00000000"
    assert apple["source"] == "KOYFIN FILE"
    assert apple["price_provenance"]["source_file_id"] == result["id"]
    again = drop.receive("different-name.csv", raw)
    assert again["state"] == "DUPLICATE" and again["duplicate_of"] == result["id"]
    assert len(accounting_session.scalars(select(models.DatasetVersion)).all()) == 1


def test_file_conflict_and_ohlc_validation(
    drop: DataDropService, accounting_session: Session
) -> None:
    raw = b"Symbol,Date,Open,High,Low,Close,Volume\nMSFT,2026-09-04,200,199,190,210,-1\n"
    uploaded = drop.receive("AAPL_2026-09-04_prices.csv", raw)
    result = drop.map_validate(uploaded["id"], profile(accounting_session).id)
    assert result["state"] == "VALIDATION_FAILED"
    assert result["validation"]["symbol_conflict"]
    assert result["validation"]["error_count"] >= 2
    result = drop.map_validate(uploaded["id"], profile(accounting_session).id, resolution="CONTENT")
    assert result["state"] == "VALIDATION_FAILED"


def test_file_versions_and_lineage(drop: DataDropService, accounting_session: Session) -> None:
    first = drop.receive("AAPL_2026-09-03_prices.csv", b"Date,Close\n2026-09-03,216\n")
    drop.map_validate(first["id"], profile(accounting_session).id)
    drop.import_file(first["id"], name="AAPL EOD", licence="Private file", approve=True)
    second = drop.receive("AAPL_2026-09-04_prices.csv", b"Date,Close\n2026-09-04,217\n")
    drop.map_validate(second["id"], profile(accounting_session).id)
    drop.import_file(second["id"], name="AAPL EOD", licence="Private file", approve=True)
    versions = accounting_session.scalars(
        select(models.DatasetVersion).order_by(models.DatasetVersion.version)
    ).all()
    assert [v.version for v in versions] == [1, 2]
    assert versions[0].dataset_id == versions[1].dataset_id
    assert len(accounting_session.scalars(select(models.DatasetLineage)).all()) == 2


def test_manual_trade_review_and_duplicate(accounting_session: Session) -> None:
    service = PortfolioLedgerService(accounting_session)
    data = {
        "transaction_type": "BUY",
        "trade_date": "2026-09-04",
        "symbol": "AAPL",
        "quantity": "1",
        "price": "217",
        "currency": "USD",
        "commission": "1",
        "external_reference": "MANUAL-001",
    }
    result = service.add(data)
    accounting_session.commit()
    assert result["fx_rate_to_base"] != "1"
    duplicate = service.add(data)
    assert duplicate["duplicate"] and duplicate["id"] == result["id"]
    trades = TradeMonitorService(accounting_session).list()
    trade = next(r for r in trades if r["id"] == result["trade_event_id"])
    assert trade["review_state"] == "REQUIRES_REVIEW"
    assert trade["weight_after"] is not None and trade["weight_before"] is not None
    assert trade["sector_weight_after"] is not None and trade["sector_weight_before"] is not None
    assert float(trade["weight_after"]) > float(trade["weight_before"])
    assert float(trade["sector_weight_after"]) > float(trade["sector_weight_before"])
    assert trade["risk_as_of"]
    TradeMonitorService(accounting_session).review(
        trade["id"], "REVIEWED", "Reviewed recorded fill and cash."
    )
    reviewed = accounting_session.get(models.TradeEvent, trade["id"])
    assert reviewed is not None
    assert reviewed.review_state == "REVIEWED"


def test_saved_etf_hedge_recalculates_covariance_on_the_same_marks(
    accounting_session: Session, seeded_market_clock: None
) -> None:
    from app.hedge_engine import HedgeRequest, HedgeService

    result = HedgeService(accounting_session).create(
        "KNK_MAIN", HedgeRequest(target=0.2, fee_bps=2), None
    )
    assert result["var_state"] == "AVAILABLE"
    assert result["var_after"] is not None
    assert result["hedge_beta"] == pytest.approx(1)
    assert result["hedge_inputs"]["price_provenance"]["source"]
    assert result["beta_after"] == pytest.approx(0.2, abs=0.02)
    run = accounting_session.get(models.AnalysisRun, result["id"])
    assert run is not None
    snapshot = run.parameters["_portfolio"]
    assert isinstance(snapshot, dict)
    assert snapshot["valuation_run_id"] == result["valuation_run_id"]


def test_transaction_import_is_atomic(drop: DataDropService, accounting_session: Session) -> None:
    uploaded = drop.receive(
        "ledger.csv",
        b"Type,Trade Date,Symbol,Quantity,Price,Currency,Reference\nBUY,2026-09-04,AAPL,1,217,USD,buy-one\nSELL,2026-09-04,AAPL,99999,217,USD,invalid-sale\n",
    )
    mapped = drop.map_validate(
        uploaded["id"], profile(accounting_session, "GENERIC_PORTFOLIO_TRANSACTIONS").id
    )
    assert mapped["state"] == "AWAITING_APPROVAL", mapped
    before = len(accounting_session.scalars(select(models.PortfolioTransaction)).all())
    result = drop.import_file(
        uploaded["id"], name="Manual ledger", licence="Internal records", approve=True
    )
    assert result["state"] == "IMPORT_FAILED"
    assert len(accounting_session.scalars(select(models.PortfolioTransaction)).all()) == before
    assert not accounting_session.scalars(select(models.DatasetVersion)).all()


def test_xlsx_and_json_preview_keep_original_bytes(
    drop: DataDropService, accounting_session: Session
) -> None:
    import io

    from openpyxl import Workbook
    from openpyxl.worksheet.worksheet import Worksheet

    book = Workbook()
    sheet = book.active
    assert isinstance(sheet, Worksheet)
    sheet.append(["Date", "Close"])
    sheet.append(["2026-09-04", 220])
    stream = io.BytesIO()
    book.save(stream)
    raw = stream.getvalue()
    result = drop.receive("AAPL_2026-09-04.xlsx", raw)
    assert result["state"] == "MAPPING_REQUIRED"
    uploaded = accounting_session.get(models.UploadedFile, drop.get(result["id"]).uploaded_file_id)
    assert uploaded is not None
    assert drop.storage.get_bytes(uploaded.object_key) == raw
    assert drop.map_validate(result["id"], profile(accounting_session).id)["validation"]["valid"]
    result = drop.receive("AAPL_2026-09-04.json", b'[{"Date":"2026-09-04","Close":222}]')
    assert result["state"] == "MAPPING_REQUIRED"
    assert drop.map_validate(result["id"], profile(accounting_session).id)["validation"]["valid"]


def test_imported_fundamentals_do_not_fill_missing_from_demo(
    drop: DataDropService, accounting_session: Session
) -> None:
    from app.terminal_analytics import fundamentals, valuation

    raw = b"Symbol,Period,Metric,Value,Frequency,Unit,Scale,Actual Estimate,Report Date\nAAPL,2025,revenue,100,ANNUAL,USD,1000000,ACTUAL,2026-02-01\n"
    result = drop.receive("AAPL_fundamentals.csv", raw)
    result = drop.map_validate(
        result["id"], profile(accounting_session, "GENERIC_FUNDAMENTALS_LONG").id
    )
    assert result["state"] == "AWAITING_APPROVAL", result
    result = drop.import_file(
        result["id"], name="AAPL statements", licence="Internal test data", approve=True
    )
    assert result["state"] == "IMPORTED"
    data = fundamentals(accounting_session, "AAPL")
    assert data["quality"] == "FILE IMPORT"
    assert data["items"][0]["revenue"] == 100
    with pytest.raises(ValueError, match="complete FCF"):
        valuation(accounting_session, "AAPL")


def test_factor_is_oos_separation_and_insufficient_history() -> None:
    import numpy as np
    import pandas as pd
    from app.factor_statistics import factor_statistics

    index = pd.bdate_range("2025-01-01", periods=120)
    frame = pd.DataFrame(
        {
            str(i): 100 + np.arange(120) * (0.02 + i * 0.003) + np.sin(np.arange(120) / (4 + i))
            for i in range(10)
        },
        index=index,
    )
    result = factor_statistics(frame, 21, 5)
    assert result["state"] == "CALCULATED"
    in_sample_end = result["in_sample"]["end"]
    out_of_sample_start = result["out_of_sample"]["start"]
    assert in_sample_end is not None and out_of_sample_start is not None
    assert in_sample_end < out_of_sample_start
    assert result["in_sample"]["mean_ic"] is not None
    assert len(result["quantile_returns"]) == len(result["ic"])
    insufficient = factor_statistics(frame.iloc[:20], 21, 5)
    assert insufficient["state"] == "INSUFFICIENT DATA"
    assert insufficient["in_sample"]["mean_ic"] is None


def test_curated_quarters_units_and_restatements_keep_metric_provenance(
    drop: DataDropService, accounting_session: Session
) -> None:
    from app.equity_financials import statements
    from app.terminal_analytics import fundamentals

    header = "Symbol,Period,Metric,Value,Frequency,Unit,Scale,Actual Estimate,Report Date\n"
    raw = header + "".join(
        f"AAPL,2025Q{i},revenue,{i * 10},QUARTERLY,USD,1000000,ACTUAL,2026-02-01\nAAPL,2025Q{i},cash,{i * 5},QUARTERLY,USD,1000000,ACTUAL,2026-02-01\n"
        for i in range(1, 5)
    )
    upload = drop.receive("AAPL_quarters.csv", raw.encode())
    mapped = drop.map_validate(
        upload["id"], profile(accounting_session, "GENERIC_FUNDAMENTALS_LONG").id
    )
    assert mapped["validation"]["valid"], mapped
    imported = drop.import_file(
        upload["id"], name="Quarterly statements", licence="Internal test fixture", approve=True
    )
    first = fundamentals(accounting_session, "AAPL")
    assert statements(first, "TTM")[0]["revenue"] == 100
    second = drop.receive(
        "AAPL_restatement.csv",
        (
            header
            + "AAPL,2025Q4,revenue,45,QUARTERLY,USD,1000000,ACTUAL,2026-03-01\nAAPL,2025Q4,debt,12,QUARTERLY,SHARES,1000000,ACTUAL,2026-03-01\n"
        ).encode(),
    )
    drop.map_validate(second["id"], profile(accounting_session, "GENERIC_FUNDAMENTALS_LONG").id)
    drop.import_file(
        second["id"], name="Restatement", licence="Internal test fixture", approve=True
    )
    revised = fundamentals(accounting_session, "AAPL")
    last = revised["items"][-1]
    assert statements(revised, "TTM")[0]["revenue"] == 105
    assert statements(revised, "TTM")[0]["cash"] == 20
    assert last["metric_sources"]["cash"]["version_id"] == imported["dataset_version_id"]
    assert (
        last["metric_sources"]["revenue"]["version_id"]
        != last["metric_sources"]["cash"]["version_id"]
    )
    assert last.get("debt") is None
    assert any("incompatible unit SHARES" in warning for warning in revised["warnings"])
