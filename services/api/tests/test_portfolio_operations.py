import hashlib
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app import models
from app.data_drop import DataDropService
from app.data_mapping import seed_profiles
from app.object_storage import ObjectStorage
from app.portfolio_operations import PortfolioLedgerService, TradeMonitorService
from app.portfolio_valuation import PortfolioValuationService
from test_portfolio_accounting import accounting_session


@pytest.fixture
def drop(accounting_session, tmp_path, monkeypatch):
    original = ObjectStorage.__init__
    def initialize(self):
        original(self)
        self.local_root = tmp_path
        self._s3 = None
    monkeypatch.setattr(ObjectStorage, "__init__", initialize)
    seed_profiles(accounting_session)
    accounting_session.commit()
    return DataDropService(accounting_session)


def profile(session, code="KOYFIN_PRICE_HISTORY"):
    return session.scalar(select(models.MappingProfile).where(models.MappingProfile.code == code))


def test_file_preview_approval_immutable_and_duplicate(drop, accounting_session):
    raw = b"Date,Open,High,Low,Close,Volume\n2026-09-04,213,219,212,217,1000\n"
    uploaded = drop.receive("AAPL_2026-09-04_prices.csv", raw)
    assert uploaded["state"] == "MAPPING_REQUIRED"
    assert uploaded["hash"] == hashlib.sha256(raw).hexdigest()
    with pytest.raises(ValueError, match="approval"):
        drop.import_file(uploaded["id"], name="Apple prices", licence="Private exported file", approve=False)
    mapped = drop.map_validate(uploaded["id"], profile(accounting_session).id)
    assert mapped["state"] == "AWAITING_APPROVAL", mapped
    result = drop.import_file(uploaded["id"], name="Apple prices", licence="Private exported file", approve=True)
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


def test_file_conflict_and_ohlc_validation(drop, accounting_session):
    raw = b"Symbol,Date,Open,High,Low,Close,Volume\nMSFT,2026-09-04,200,199,190,210,-1\n"
    uploaded = drop.receive("AAPL_2026-09-04_prices.csv", raw)
    result = drop.map_validate(uploaded["id"], profile(accounting_session).id)
    assert result["state"] == "VALIDATION_FAILED"
    assert result["validation"]["symbol_conflict"]
    assert result["validation"]["error_count"] >= 2
    result = drop.map_validate(uploaded["id"], profile(accounting_session).id, resolution="CONTENT")
    assert result["state"] == "VALIDATION_FAILED"


def test_file_versions_and_lineage(drop, accounting_session):
    first = drop.receive("AAPL_2026-09-03_prices.csv", b"Date,Close\n2026-09-03,216\n")
    drop.map_validate(first["id"], profile(accounting_session).id)
    drop.import_file(first["id"], name="AAPL EOD", licence="Private file", approve=True)
    second = drop.receive("AAPL_2026-09-04_prices.csv", b"Date,Close\n2026-09-04,217\n")
    drop.map_validate(second["id"], profile(accounting_session).id)
    drop.import_file(second["id"], name="AAPL EOD", licence="Private file", approve=True)
    versions = accounting_session.scalars(select(models.DatasetVersion).order_by(models.DatasetVersion.version)).all()
    assert [v.version for v in versions] == [1, 2]
    assert versions[0].dataset_id == versions[1].dataset_id
    assert len(accounting_session.scalars(select(models.DatasetLineage)).all()) == 2


def test_manual_trade_review_and_duplicate(accounting_session):
    service = PortfolioLedgerService(accounting_session)
    data = {"transaction_type": "BUY", "trade_date": "2026-09-04", "symbol": "AAPL", "quantity": "1", "price": "217", "currency": "USD", "commission": "1", "external_reference": "MANUAL-001"}
    result = service.add(data)
    accounting_session.commit()
    assert result["fx_rate_to_base"] != "1"
    duplicate = service.add(data)
    assert duplicate["duplicate"] and duplicate["id"] == result["id"]
    trades = TradeMonitorService(accounting_session).list()
    trade = next(r for r in trades if r["id"] == result["trade_event_id"])
    assert trade["review_state"] == "REQUIRES_REVIEW"
    TradeMonitorService(accounting_session).review(trade["id"], "REVIEWED", "Reviewed recorded fill and cash.")
    assert accounting_session.get(models.TradeEvent, trade["id"]).review_state == "REVIEWED"


def test_transaction_import_is_atomic(drop, accounting_session):
    uploaded = drop.receive("ledger.csv", b"Type,Trade Date,Symbol,Quantity,Price,Currency,Reference\nBUY,2026-09-04,AAPL,1,217,USD,buy-one\nSELL,2026-09-04,AAPL,99999,217,USD,invalid-sale\n")
    mapped = drop.map_validate(uploaded["id"], profile(accounting_session, "GENERIC_PORTFOLIO_TRANSACTIONS").id)
    assert mapped["state"] == "AWAITING_APPROVAL", mapped
    before = len(accounting_session.scalars(select(models.PortfolioTransaction)).all())
    result = drop.import_file(uploaded["id"], name="Manual ledger", licence="Internal records", approve=True)
    assert result["state"] == "IMPORT_FAILED"
    assert len(accounting_session.scalars(select(models.PortfolioTransaction)).all()) == before
    assert not accounting_session.scalars(select(models.DatasetVersion)).all()

def test_xlsx_and_json_preview_keep_original_bytes(drop, accounting_session):
    from openpyxl import Workbook
    import io
    book = Workbook()
    book.active.append(["Date", "Close"])
    book.active.append(["2026-09-04", 220])
    stream = io.BytesIO()
    book.save(stream)
    raw = stream.getvalue()
    result = drop.receive("AAPL_2026-09-04.xlsx", raw)
    assert result["state"] == "MAPPING_REQUIRED"
    uploaded = accounting_session.get(models.UploadedFile, drop.get(result["id"]).uploaded_file_id)
    assert drop.storage.get_bytes(uploaded.object_key) == raw
    assert drop.map_validate(result["id"], profile(accounting_session).id)["validation"]["valid"]
    result = drop.receive("AAPL_2026-09-04.json", b'[{"Date":"2026-09-04","Close":222}]')
    assert result["state"] == "MAPPING_REQUIRED"
    assert drop.map_validate(result["id"], profile(accounting_session).id)["validation"]["valid"]


def test_imported_fundamentals_do_not_fill_missing_from_demo(drop, accounting_session):
    from app.terminal_analytics import fundamentals, valuation
    raw = b"Symbol,Period,Metric,Value,Frequency,Unit,Scale,Actual Estimate,Report Date\nAAPL,2025,revenue,100,ANNUAL,USD,1000000,ACTUAL,2026-02-01\n"
    result = drop.receive("AAPL_fundamentals.csv", raw)
    result = drop.map_validate(result["id"], profile(accounting_session, "GENERIC_FUNDAMENTALS_LONG").id)
    assert result["state"] == "AWAITING_APPROVAL", result
    result = drop.import_file(result["id"], name="AAPL statements", licence="Internal test data", approve=True)
    assert result["state"] == "IMPORTED"
    data = fundamentals(accounting_session, "AAPL")
    assert data["quality"] == "FILE IMPORT"
    assert data["items"][0]["revenue"] == 100
    with pytest.raises(ValueError, match="complete FCF"):
        valuation(accounting_session, "AAPL")


def test_factor_is_oos_separation_and_insufficient_history():
    import pandas as pd
    import numpy as np
    from app.factor_statistics import factor_statistics
    index = pd.bdate_range("2025-01-01", periods=120)
    frame = pd.DataFrame({str(i): 100 + np.arange(120) * (.02 + i * .003) + np.sin(np.arange(120) / (4 + i)) for i in range(10)}, index=index)
    result = factor_statistics(frame, 21, 5)
    assert result["state"] == "CALCULATED"
    assert result["in_sample"]["end"] < result["out_of_sample"]["start"]
    assert result["in_sample"]["mean_ic"] is not None
    assert len(result["quantile_returns"]) == len(result["ic"])
    insufficient = factor_statistics(frame.iloc[:20], 21, 5)
    assert insufficient["state"] == "INSUFFICIENT DATA"
    assert insufficient["in_sample"]["mean_ic"] is None
