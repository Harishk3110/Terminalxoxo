"""Gross assets less all liability classes reconcile to economic NAV."""

from decimal import Decimal as D

import pytest
from app.portfolio_domain.nav import NavCalculationService, nav_total
from hypothesis import given
from hypothesis import strategies as st


def test_short_positions_and_foreign_cash_overdrafts_are_not_netted_out_of_liabilities() -> None:
    result = NavCalculationService.calculate(
        D(48),
        [D(500), D(-120)],
        {
            "accrued_income": D(50),
            "payables": D(30),
            "accrued_fees": D(10),
            "other_liabilities": D(15),
        },
        cash_components=[D(100), D(-52)],
    )
    assert result["cash_assets"] == D(100)
    assert result["cash_overdrafts"] == D(52)
    assert result["long_market_value"] == D(500)
    assert result["short_liabilities"] == D(120)
    assert result["gross_asset_value"] == D(650)
    assert result["liabilities"] == D(227)
    assert result["nav"] == D(423)
    assert result["cash"] == D(48)
    assert result["market_value"] == D(380)


def test_legacy_aggregate_cash_call_still_includes_net_overdraft_and_short_liability() -> None:
    result = nav_total(D(-20), [D(-30)], {})
    assert result["gross_asset_value"] == 0
    assert result["cash_overdrafts"] == 20
    assert result["short_liabilities"] == 30
    assert result["liabilities"] == 50
    assert result["nav"] == -50


def test_same_currency_netting_is_explicit_in_the_supplied_cash_components() -> None:
    gross = nav_total(D(0), [], {}, cash_components=[D(100), D(-100)])
    net = nav_total(D(0), [], {}, cash_components=[D(0)])
    assert gross["nav"] == net["nav"] == 0
    assert gross["gross_asset_value"] == gross["liabilities"] == 100
    assert net["gross_asset_value"] == net["liabilities"] == 0


def test_unsettled_trade_reclassification_preserves_nav_without_duplicating_cash() -> None:
    before = nav_total(D(1000), [D(420)], {"payables": D(400)}, cash_components=[D(1000)])
    after = nav_total(D(600), [D(420)], {}, cash_components=[D(600)])
    assert before["nav"] == after["nav"] == D(1020)
    assert before["gross_asset_value"] == D(1420)
    assert before["liabilities"] == D(400)
    assert after["gross_asset_value"] == D(1020)
    assert after["liabilities"] == 0


@pytest.mark.parametrize(
    "bucket,sign",
    [
        ("accrued_income", 1),
        ("receivables", 1),
        ("payables", -1),
        ("accrued_fees", -1),
        ("other_liabilities", -1),
    ],
)
def test_each_recorded_bucket_is_recognized_once(bucket, sign) -> None:
    result = nav_total(D(100), [], {bucket: D("12.34567891")})
    assert result["nav"] == D(100) + sign * D("12.34567891")
    assert result["gross_asset_value"] - result["liabilities"] == result["nav"]
    assert result[bucket] == D("12.34567891")
    assert result["cash_assets"] == D(100)


def test_inconsistent_currency_cash_sum_is_rejected_instead_of_creating_a_balanced_looking_report() -> (
    None
):
    with pytest.raises(ValueError, match="must equal settled cash"):
        nav_total(D(100), [], {}, cash_components=[D(50), D(49)])
    with pytest.raises(ValueError, match="must equal settled cash"):
        nav_total(D(1), [], {}, cash_components=[])


@pytest.mark.parametrize("value", [D("NaN"), D("Infinity"), D("-Infinity")])
def test_nonfinite_cash_components_and_positions_are_rejected(value) -> None:
    with pytest.raises(ValueError):
        nav_total(D(0), [], {}, cash_components=[value])
    with pytest.raises(ValueError):
        nav_total(D(0), [value], {})


def test_unknown_and_negative_recorded_buckets_are_not_silently_treated_as_assets() -> None:
    with pytest.raises(ValueError, match="Unknown NAV balance bucket"):
        nav_total(D(100), [], {"mystery": D(10)})
    with pytest.raises(ValueError):
        nav_total(D(100), [], {"payables": D(-10)})


def test_empty_statement_is_explicitly_zero_without_missing_keys() -> None:
    result = nav_total(D(0), [], {}, cash_components=[])
    assert set(result) == {
        "nav",
        "cash",
        "cash_assets",
        "cash_overdrafts",
        "market_value",
        "long_market_value",
        "short_liabilities",
        "gross_asset_value",
        "accrued_income",
        "receivables",
        "payables",
        "accrued_fees",
        "other_liabilities",
        "liabilities",
    }
    assert all(value == 0 for value in result.values())


finite = st.decimals(
    min_value=-1000000, max_value=1000000, places=8, allow_nan=False, allow_infinity=False
)


@given(
    st.lists(finite, max_size=15),
    st.lists(finite, max_size=15),
    st.decimals(min_value=0, max_value=1000000, places=8, allow_nan=False, allow_infinity=False),
)
def test_gross_asset_and_liability_identity_for_mixed_signed_positions_and_cash(
    cash, positions, payable
) -> None:
    result = nav_total(sum(cash, D(0)), positions, {"payables": payable}, cash_components=cash)
    assert result["nav"] == sum(cash, D(0)) + sum(positions, D(0)) - payable
    assert result["gross_asset_value"] - result["liabilities"] == result["nav"]
    assert result["cash_assets"] - result["cash_overdrafts"] == result["cash"]
    assert result["long_market_value"] - result["short_liabilities"] == result["market_value"]
    assert result["gross_asset_value"] >= 0
    assert result["liabilities"] >= 0
