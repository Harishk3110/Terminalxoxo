"""Explicit, unlevered FCFF research assumptions; no market execution or advice."""

from decimal import Decimal, localcontext
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

D = Decimal
Rate = Annotated[Decimal, Field(ge=-1, le=2, allow_inf_nan=False)]
Fraction = Annotated[Decimal, Field(ge=0, le=1, allow_inf_nan=False)]
Amount = Annotated[Decimal, Field(ge=0, le=10**12, allow_inf_nan=False)]


class WaccInputs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    risk_free: Fraction = D(".03")
    beta: Annotated[Decimal, Field(ge=-5, le=10)] = D("1")
    equity_risk_premium: Fraction = D(".05")
    cost_of_debt: Fraction = D(".05")
    tax_rate: Fraction = D(".21")
    equity_market_value: Amount = D("80")
    debt_market_value: Amount = D("20")

    @model_validator(mode="after")
    def positive_capital(self):
        if self.equity_market_value + self.debt_market_value <= 0:
            raise ValueError("WACC requires positive total market capital")
        return self


def calculate_wacc(inputs: WaccInputs):
    total = inputs.equity_market_value + inputs.debt_market_value
    equity_weight = inputs.equity_market_value / total
    cost_equity = inputs.risk_free + inputs.beta * inputs.equity_risk_premium
    after_tax_debt = inputs.cost_of_debt * (1 - inputs.tax_rate)
    return {
        "cost_of_equity": str(cost_equity),
        "after_tax_cost_of_debt": str(after_tax_debt),
        "equity_weight": str(equity_weight),
        "debt_weight": str(1 - equity_weight),
        "wacc": str(equity_weight * cost_equity + (1 - equity_weight) * after_tax_debt),
        "inputs": inputs.model_dump(mode="json"),
    }


class DcfScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Literal["BULL", "BASE", "BEAR"]
    revenue_growth: list[Rate] = Field(
        default_factory=lambda: [D(".08")] * 5, min_length=1, max_length=10
    )
    ebit_margins: list[Rate] = Field(
        default_factory=lambda: [D(".25")] * 5, min_length=1, max_length=10
    )
    tax_rate: Fraction = D(".21")
    depreciation_pct: Fraction = D(".03")
    capex_pct: Fraction = D(".05")
    working_capital_pct: Fraction = D(".10")
    wacc: Annotated[Decimal, Field(gt=0, le=1)] = D(".10")
    terminal_growth: Annotated[Decimal, Field(ge=-0.1, le=0.1)] = D(".025")
    terminal_method: Literal["PERPETUITY", "EXIT_MULTIPLE"] = "PERPETUITY"
    exit_multiple: Annotated[Decimal, Field(gt=0, le=100)] = D("12")

    @model_validator(mode="after")
    def schedules(self):
        if len(self.revenue_growth) != len(self.ebit_margins):
            raise ValueError("Revenue growth and margin schedules must have equal lengths")
        if any(value <= -1 for value in self.revenue_growth):
            raise ValueError("Revenue growth must exceed -100%")
        if self.terminal_method == "PERPETUITY" and self.terminal_growth >= self.wacc:
            raise ValueError("Perpetuity WACC must exceed terminal growth")
        return self


class DcfRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbol: str = Field(min_length=1, max_length=40)
    period: str | None = None
    frequency: Literal["ANNUAL", "TTM"] = "ANNUAL"
    scenarios: list[DcfScenario] = Field(min_length=1, max_length=3)
    initial_working_capital: Amount | None = None
    debt_override: Amount | None = None
    cash_override: Amount | None = None
    shares_override: Annotated[Decimal, Field(gt=0, le=10**12)] | None = None
    wacc_inputs: WaccInputs | None = None
    apply_calculated_wacc: bool = False

    @model_validator(mode="after")
    def unique_scenarios(self):
        if len({s.name for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("Scenario names must be unique")
        if self.apply_calculated_wacc and self.wacc_inputs is None:
            raise ValueError("Calculated WACC requires explicit capital-market inputs")
        return self


def _project(base: dict, scenario: DcfScenario, initial_wc: Decimal | None, price):
    revenue, debt, cash, shares = (
        D(str(base[key])) for key in ("revenue", "debt", "cash", "shares")
    )
    if revenue <= 0 or shares <= 0 or debt < 0 or cash < 0:
        raise ValueError("DCF requires positive revenue/shares and non-negative debt/cash")
    wc = initial_wc if initial_wc is not None else revenue * scenario.working_capital_pct
    rows = []
    for year, (growth, margin) in enumerate(
        zip(scenario.revenue_growth, scenario.ebit_margins, strict=True), 1
    ):
        revenue *= 1 + growth
        ebit = revenue * margin
        # Losses do not receive an immediate cash tax credit; NOLs are not modelled.
        tax = max(D(0), ebit) * scenario.tax_rate
        da, capex = revenue * scenario.depreciation_pct, revenue * scenario.capex_pct
        next_wc = revenue * scenario.working_capital_pct
        delta_wc = next_wc - wc
        fcff = ebit - tax + da - capex - delta_wc
        pv = fcff / (1 + scenario.wacc) ** year
        rows.append(
            {
                "year": year,
                "growth": growth,
                "revenue": revenue,
                "ebit_margin": margin,
                "ebit": ebit,
                "tax": tax,
                "nopat": ebit - tax,
                "depreciation": da,
                "capex": capex,
                "working_capital": next_wc,
                "delta_working_capital": delta_wc,
                "fcff": fcff,
                "present_value": pv,
            }
        )
        wc = next_wc
    last = rows[-1]
    terminal = (
        last["fcff"] * (1 + scenario.terminal_growth) / (scenario.wacc - scenario.terminal_growth)
        if scenario.terminal_method == "PERPETUITY"
        else (last["ebit"] + last["depreciation"]) * scenario.exit_multiple
    )
    terminal_pv = terminal / (1 + scenario.wacc) ** len(rows)
    enterprise = sum(row["present_value"] for row in rows) + terminal_pv
    equity = enterprise - debt + cash
    fair = equity / shares
    return {
        "name": scenario.name,
        "forecast": rows,
        "enterprise_value": enterprise,
        "equity_value": equity,
        "fair_value": fair,
        "net_debt": debt - cash,
        "shares": shares,
        "terminal_value": terminal,
        "terminal_pv": terminal_pv,
        "terminal_share": terminal_pv / enterprise if enterprise > 0 else None,
        "upside": fair / D(str(price)) - 1 if price is not None and D(str(price)) > 0 else None,
    }


def _json(value):
    if isinstance(value, D):
        return str(value)
    if isinstance(value, list):
        return [_json(row) for row in value]
    if isinstance(value, dict):
        return {key: _json(row) for key, row in value.items()}
    return value


def dcf_scenarios(base: dict, request: DcfRequest, price=None):
    base = dict(base)
    for metric in ("debt", "cash", "shares"):
        override = getattr(request, metric + "_override")
        if override is not None:
            base[metric] = str(override)
    if any(base.get(key) is None for key in ("revenue", "debt", "cash", "shares")):
        raise ValueError(
            "Statement requires revenue, debt, cash and shares; missing fields are not demo-filled"
        )
    result = []
    wacc_result = calculate_wacc(request.wacc_inputs) if request.wacc_inputs else None
    with localcontext() as context:
        context.prec = 34
        for submitted in request.scenarios:
            assumptions = submitted.model_dump()
            if request.apply_calculated_wacc:
                assumptions["wacc"] = D(wacc_result["wacc"])
            scenario = DcfScenario.model_validate(assumptions)
            projected = _project(base, scenario, request.initial_working_capital, price)
            sensitivity = []
            for change in ("-.02", "-.01", "0", ".01", ".02"):
                rate = scenario.wacc + D(change)
                for delta in ("-.01", "-.005", "0", ".005", ".01"):
                    growth = scenario.terminal_growth + D(delta)
                    valid = rate > 0 and growth < rate
                    case = scenario.model_copy(
                        update={
                            "wacc": rate,
                            "terminal_growth": growth,
                            "terminal_method": "PERPETUITY",
                        }
                    )
                    sensitivity.append(
                        {
                            "wacc": rate,
                            "terminal_growth": growth,
                            "fair_value": _project(
                                base, case, request.initial_working_capital, price
                            )["fair_value"]
                            if valid
                            else None,
                            "state": "AVAILABLE" if valid else "INVALID_ASSUMPTIONS",
                        }
                    )
            exits = []
            for change in ("-.02", "0", ".02"):
                for multiple in (
                    max(D(".1"), scenario.exit_multiple - 2),
                    scenario.exit_multiple,
                    scenario.exit_multiple + 2,
                ):
                    rate = scenario.wacc + D(change)
                    case = scenario.model_copy(
                        update={
                            "wacc": rate,
                            "exit_multiple": multiple,
                            "terminal_method": "EXIT_MULTIPLE",
                        }
                    )
                    exits.append(
                        {
                            "wacc": rate,
                            "exit_multiple": multiple,
                            "fair_value": _project(
                                base, case, request.initial_working_capital, price
                            )["fair_value"]
                            if rate > 0
                            else None,
                        }
                    )
            result.append(
                {
                    **projected,
                    "assumptions": scenario.model_dump(mode="json"),
                    "growth_sensitivity": sensitivity,
                    "exit_sensitivity": exits,
                }
            )
    return {
        "scenarios": _json(result),
        "wacc": wacc_result,
        "base_statement": _json(base),
        "calculation_version": "knk-fcff-1.0",
        "warnings": [
            "User assumptions, not company forecasts. End-year FCFF discounting; terminal cash flow grows final forecast FCFF.",
            "No automatic NOL benefit, dilution, pension, minority-interest or non-operating asset adjustment.",
            "Initial non-cash working capital is explicitly supplied or estimated using the scenario revenue ratio.",
            "Negative enterprise/equity values are retained, not clipped to a positive target.",
        ],
    }
