from app.alpha_api import AlphaRequest, analyse
from test_portfolio_accounting import accounting_session
from app.monte_carlo import pin_monte_carlo, monte_carlo_result


def test_portfolio_alpha_uses_net_gross_and_additional_costs(accounting_session):
    data = analyse(accounting_session, AlphaRequest(estimated_cost_bps_per_period=1))
    assert data["state"] == "AVAILABLE"
    assert data["results"]["NET"]["p_value"] is not None
    assert data["results"]["NET_AFTER_ESTIMATED_COSTS"]["annualised_alpha"] < data["results"]["NET"]["annualised_alpha"]
    assert data["results"]["GROSS"]["annualised_alpha"] > data["results"]["NET"]["annualised_alpha"]
    assert data["inputs"]["valuation_run_id"]


def test_portfolio_monte_carlo_pins_eligible_net_returns(accounting_session):
    params = pin_monte_carlo(accounting_session, {"settings": {"paths": 100, "horizon": 10}})
    assert params["_evidence"]["valuation_run_id"]
    result = monte_carlo_result(params)
    assert result["observations"] >= 60
    assert result["inputs"]["cost_basis"] == "NET ledger returns"
