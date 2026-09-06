"""Valuation adapters select exact fields, retain explicit nulls and capture mark states."""

from decimal import Decimal as D

import pytest
from app.portfolio_exposure import exposure_service


def test_explicit_null_exact_value_does_not_fall_back_to_rounded_zero() -> None:
    service = exposure_service(
        [
            {
                "instrument_id": "AAA",
                "currency": "USD",
                "market_value_base_exact": None,
                "market_value": "0",
                "market_price": "10",
                "fx_rate": None,
                "price_provenance": {"stale": False},
                "fx_provenance": {"stale": False},
            },
        ],
        [{"currency": "USD", "base_value_exact": None, "base_value": "0", "fx_rate": None}],
        [],
        None,
    )
    row = service.groups()["currency"][0]
    assert row["missing_count"] == 2
    assert row["net_value"] is None
    assert service.freshness()["unavailable_items"] == 2


def test_exact_mark_is_used_instead_of_rounded_display_value() -> None:
    service = exposure_service(
        [
            {
                "instrument_id": "AAA",
                "currency": "USD",
                "market_value_base_exact": "0.004",
                "market_value": "0.00",
                "market_price": "0.004",
                "fx_rate": "1",
                "price_provenance": {"stale": True},
                "fx_provenance": {"stale": True},
            },
        ],
        [
            {
                "currency": "USD",
                "base_value_exact": "0.003",
                "base_value": "0.00",
                "fx_rate": "1",
                "fx_provenance": {"stale": True},
            }
        ],
        [],
        D("0.007"),
    )
    row = service.groups()["currency"][0]
    assert row["net_value"] == D("0.007")
    assert row["value"] == D("0.01")
    assert row["weight"] == 1
    assert service.freshness()["stale_total_value"] == D("0.007")
    assert service.freshness()["stale_nav_pct"] == 1
    assert service.freshness()["stale_items"] == 2


def test_legacy_rounded_fields_are_accepted_only_when_exact_fields_are_absent() -> None:
    service = exposure_service(
        [
            {
                "instrument_id": "AAA",
                "currency": "SGD",
                "market_value": "12.30",
                "market_price": "12.3",
                "fx_rate": "1",
                "price_provenance": {},
                "fx_provenance": {},
                "asset_class": "Equity",
            },
        ],
        [{"currency": "SGD", "base_value": "4.56", "fx_rate": "1"}],
        [],
        D("16.86"),
    )
    row = service.groups()["currency"][0]
    assert row["net_value"] == D("16.86")
    assert row["cash_value"] == D("4.56")
    assert service.freshness()["stale_items"] == 0


@pytest.mark.parametrize("bucket,expected", [("receivables", "Accrual"), ("payables", "Liability")])
def test_balance_adapter_retains_fx_state_and_decimal_strings(bucket, expected) -> None:
    service = exposure_service(
        [],
        [],
        [
            {
                "bucket": bucket,
                "currency": "USD",
                "base_value": "-4.125",
                "fx_rate": "1.375",
                "fx_provenance": {"stale": True},
            }
        ],
        D(-10),
    )
    row = service.groups()["asset_class"][0]
    assert row["name"] == expected
    assert row["balance_value"] == D("-4.125")
    assert row["stale_count"] == 1
    assert service.groups()["country"] == []
    assert service.freshness()["stale_total_value"] == D("4.125")


def test_adapter_without_rounded_projection_does_not_access_missing_fallback_key() -> None:
    service = exposure_service(
        [
            {
                "instrument_id": "AAA",
                "currency": "USD",
                "market_value_base_exact": "10",
                "market_price": "5",
                "fx_rate": "1",
                "price_provenance": {},
                "fx_provenance": {},
            },
        ],
        [{"currency": "USD", "base_value_exact": "-5", "fx_rate": "1"}],
        [],
        D(5),
    )
    assert service.groups()["currency"][0]["net_value"] == D(5)
