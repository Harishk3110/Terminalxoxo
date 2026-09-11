from app.equity_financials import comparable_statistics, ratios, statements


def test_ttm_needs_consecutive_quarters_and_keeps_point_in_time_balances():
    data = {
        "items": [
            {
                "year": f"2025Q{i}",
                "frequency": "QUARTERLY",
                "revenue": 10 * i,
                "cash": 5 * i,
                "shares": 10,
                "report_date": f"2025-0{i + 1}-01",
            }
            for i in range(1, 5)
        ]
    }
    rows = statements(data, "TTM")
    assert len(rows) == 1 and rows[0]["revenue"] == 100 and rows[0]["cash"] == 20
    assert rows[0]["net_income"] is None and rows[0]["shares"] == 10
    data["items"][1]["actual_estimate"] = "ESTIMATE"
    assert statements(data, "TTM") == []


def test_ratios_missing_negative_denominators_and_average_balances():
    row = {
        "year": "2025",
        "revenue": 100,
        "net_income": -5,
        "shares": 10,
        "equity": 50,
        "ebit": 10,
        "depreciation": 3,
        "operating_cash_flow": 20,
        "capex": -5,
        "debt": 20,
        "cash": 5,
    }
    result = ratios(row, {"equity": 30, "revenue": 80}, 10)
    assert result["pe"] is None
    assert result["ebitda"] == 13
    assert result["fcf_yield"] == 0.15
    assert result["roe"] == -0.125
    assert result["revenue_growth"] == 0.25
    assert result["ev_sales"] == 1.15
    assert result["forward_pe"] is None


def test_comps_exclude_missing_multiples_and_translate_ev_to_equity():
    peers = [
        {"symbol": str(i), "ev_sales": value} for i, value in enumerate([1, 2, 3, 4, 100, None])
    ]
    target = {"revenue": 100, "debt": 20, "cash": 10, "shares": 10}
    row = next(row for row in comparable_statistics(peers, target) if row["metric"] == "ev_sales")
    assert row["count"] == 5 and row["median"] == 3
    assert row["implied_price"] == 29
    assert row["outliers"] == ["4"]
    assert comparable_statistics([], target)[0]["median"] is None
