"""Exposure algebra and missing-value semantics independent of persistence."""

from dataclasses import replace
from decimal import Decimal as D

import pytest
from app.portfolio_domain.exposure import ExposureItem, PortfolioExposureService
from hypothesis import given
from hypothesis import strategies as st


def position(identifier: str, value: str | None, **fields) -> ExposureItem:
    return ExposureItem(
        identifier,
        "POSITION",
        "USD",
        D(value) if value is not None else None,
        "Equity",
        sector="Technology",
        country="US",
        **fields,
    )


def test_signed_components_and_gross_weights_do_not_net_away_shorts() -> None:
    service = PortfolioExposureService(
        [
            position("long", "1000.125"),
            position("short", "-400.025"),
            ExposureItem("USD", "CASH", "USD", D("100"), "Cash"),
            ExposureItem("fees:USD", "BALANCE", "USD", D("-20"), "Liability"),
        ],
        D("680.1"),
    )
    currency = service.groups()["currency"][0]
    assert currency["net_value"] == D("680.1")
    assert currency["gross_value"] == D("1520.15")
    assert currency["long_value"] == D("1000.125")
    assert currency["short_value"] == D("-400.025")
    assert currency["cash_value"] == D(100)
    assert currency["balance_value"] == D(-20)
    assert currency["weight"] == 1
    assert currency["gross_weight"] > 2
    assert currency["position_count"] == 2
    assert currency["item_count"] == 4
    assert service.groups()["sector"][0]["net_value"] == D("600.100")
    assert {r["name"] for r in service.groups()["asset_class"]} == {"Equity", "Cash", "Liability"}


def test_missing_position_retains_group_and_known_cash_without_fake_net_total() -> None:
    service = PortfolioExposureService(
        [
            position("unpriced", None, price_available=False),
            position("marked", "100"),
            ExposureItem("USD", "CASH", "USD", D(20), "Cash"),
        ],
        None,
    )
    row = service.groups()["currency"][0]
    assert row["name"] == "USD"
    assert row["known_value"] == D(120)
    assert row["value"] is row["net_value"] is row["gross_value"] is None
    assert row["long_value"] is row["short_value"] is None
    assert row["cash_value"] == D(20)
    assert row["balance_value"] == 0
    assert row["weight"] is row["gross_weight"] is None
    assert row["missing_count"] == 1
    assert row["state"] == "INCOMPLETE"
    assert service.freshness()["price_coverage_pct"] == 50
    assert service.freshness()["stale_nav_pct"] is None


def test_missing_cash_does_not_hide_known_position_components() -> None:
    service = PortfolioExposureService(
        [
            position("long", "50"),
            ExposureItem("USD", "CASH", "USD", None, "Cash", fx_available=False),
        ],
        None,
    )
    row = service.groups()["currency"][0]
    assert row["long_value"] == D(50)
    assert row["short_value"] == 0
    assert row["cash_value"] is None
    assert row["net_value"] is None
    assert service.freshness()["cash_fx_coverage_pct"] == 0
    assert service.freshness()["price_coverage_pct"] == 100


@pytest.mark.parametrize("nav", [None, D(0)])
def test_zero_or_unknown_nav_preserves_values_but_never_emits_zero_weights(nav) -> None:
    service = PortfolioExposureService([position("short", "-20")], nav)
    row = service.groups()["sector"][0]
    assert row["net_value"] == D(-20)
    assert row["gross_value"] == D(20)
    assert row["weight"] is row["gross_weight"] is None
    assert service.freshness()["stale_nav_pct"] is None


def test_negative_nav_uses_signed_net_and_absolute_gross_denominators() -> None:
    service = PortfolioExposureService([position("short", "-200", stale=True)], D(-100))
    row = service.groups()["sector"][0]
    assert row["weight"] == D(2)
    assert row["gross_weight"] == D(2)
    assert service.freshness()["stale_nav_pct"] == D(2)


def test_stale_components_are_absolute_and_counted_once_per_item() -> None:
    service = PortfolioExposureService(
        [
            position("long", "100", stale=True),
            position("short", "-90", stale=True),
            ExposureItem("USD", "CASH", "USD", D(-50), "Cash", stale=True),
            ExposureItem("fees:USD", "BALANCE", "USD", D(-5), "Liability", stale=True),
            ExposureItem("SGD", "CASH", "SGD", D(100), "Cash"),
        ],
        D(55),
    )
    result = service.freshness()
    assert result["stale_market_value"] == D(190)
    assert result["stale_cash_value"] == D(50)
    assert result["stale_balance_value"] == D(5)
    assert result["stale_total_value"] == D(245)
    assert result["stale_nav_pct"] == D(245) / D(55)
    assert result["stale_items"] == 4
    assert result["known_marked_value"] == D(345)
    assert result["state"] == "AVAILABLE"


def test_unavailable_component_invalidates_stale_percentage_even_with_supplied_nav() -> None:
    service = PortfolioExposureService(
        [
            position("marked", "25", stale=True),
            position("unknown", None),
        ],
        D(100),
    )
    result = service.freshness()
    assert result["stale_total_value"] == D(25)
    assert result["stale_nav_pct"] is None
    assert result["unavailable_items"] == 1
    assert result["state"] == "INCOMPLETE"


def test_unclassified_positions_are_retained_but_cash_has_no_invented_country() -> None:
    item = replace(position("unknown", "10"), sector=" ", country=None, asset_class="")
    cash = ExposureItem("SGD", "CASH", "SGD", D(40), "Cash")
    groups = PortfolioExposureService([item, cash], D(50)).groups()
    assert groups["country"][0]["name"] == "Unclassified"
    assert groups["country"][0]["net_value"] == D(10)
    assert groups["sector"][0]["name"] == "Unclassified"
    assert {r["name"] for r in groups["asset_class"]} == {"Unclassified", "Cash"}
    with pytest.raises(ValueError, match="dimension"):
        item.group("issuer")


def test_deterministic_group_order_uses_absolute_known_values_then_name() -> None:
    items = [
        replace(position("z", "-10"), sector="Z"),
        replace(position("a", "10"), sector="A"),
        replace(position("m", None), sector="M"),
    ]
    assert [r["name"] for r in PortfolioExposureService(items, None).groups()["sector"]] == [
        "A",
        "Z",
        "M",
    ]


def test_empty_portfolio_has_no_invented_exposure_rows() -> None:
    service = PortfolioExposureService([], D(0))
    assert all(not rows for rows in service.groups().values())
    assert service.freshness()["item_count"] == 0
    assert service.freshness()["cash_fx_coverage_pct"] == 100
    assert service.freshness()["stale_nav_pct"] is None


@pytest.mark.parametrize("value", [D("NaN"), D("Infinity"), D("-Infinity")])
def test_nonfinite_values_and_nav_are_rejected(value: D) -> None:
    with pytest.raises(ValueError, match="finite"):
        position("bad", str(value))
    with pytest.raises(ValueError, match="finite"):
        PortfolioExposureService([], value)


@pytest.mark.parametrize("fields", [{"identifier": ""}, {"currency": "US"}, {"kind": "OTHER"}])
def test_invalid_identifiers_kinds_and_currencies_are_rejected(fields: dict) -> None:
    with pytest.raises(ValueError):
        replace(position("valid", "1"), **fields)


def test_duplicate_components_are_rejected_but_kind_namespaces_are_independent() -> None:
    item = position("USD", "10")
    with pytest.raises(ValueError, match="duplicated"):
        PortfolioExposureService([item, item], D(20))
    cash = ExposureItem("USD", "CASH", "USD", D(5), "Cash")
    assert PortfolioExposureService([item, cash], D(15)).groups()["currency"][0]["net_value"] == 15


@given(
    st.lists(
        st.decimals(
            min_value=-1000000, max_value=1000000, places=8, allow_nan=False, allow_infinity=False
        ),
        min_size=1,
        max_size=20,
    )
)
def test_currency_and_asset_class_partitions_conserve_exact_signed_values(values) -> None:
    items = [
        replace(
            position(str(i), str(value)),
            currency="USD" if i % 2 else "SGD",
            asset_class="Equity" if i % 3 else "Fund",
        )
        for i, value in enumerate(values)
    ]
    total = sum(values, D(0))
    for rows in PortfolioExposureService(items, total).groups().values():
        assert sum((r["net_value"] for r in rows), D(0)) == total
        assert sum((r["gross_value"] for r in rows), D(0)) == sum(map(abs, values), D(0))
        for row in rows:
            assert row["long_value"] + row["short_value"] == row["net_value"]
            assert row["gross_value"] >= abs(row["net_value"])
