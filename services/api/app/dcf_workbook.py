"""Native Excel FCFF formulas, built only from a reconciled immutable DCF result."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter

from .equity_valuation import DcfRequest, DcfScenarioResult, calculate_wacc, dcf_scenarios
from .report_contracts import Cell, ReportSnapshot


class DcfInput(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    calculation_version: Literal["knk-fcff-1.0"]
    parameters: DcfRequest
    base_statement: dict[str, JsonValue]
    scenarios: list[DcfScenarioResult] = Field(min_length=1, max_length=3)
    quote: dict[str, JsonValue] = Field(default_factory=dict)


@dataclass(frozen=True)
class Formula:
    expression: str
    cached: float | str


@dataclass(frozen=True)
class ModelCell:
    address: str
    value: Cell | Formula
    role: Literal["header", "label", "input", "source", "formula"] = "label"
    percent: bool = False


@dataclass
class ModelSheet:
    name: str
    cells: list[ModelCell] = field(default_factory=list)
    last_column: int = 7

    def write(
        self,
        address: str,
        value: Cell,
        role: Literal["header", "label", "input", "source", "formula"] = "label",
        percent: bool = False,
    ) -> None:
        self.cells.append(ModelCell(address, value, role, percent))

    def formula(
        self, address: str, expression: str, cached: Decimal | None, percent: bool = False
    ) -> None:
        self.cells.append(
            ModelCell(
                address,
                Formula(expression, float(cached) if cached is not None else "#N/A"),
                "formula",
                percent,
            )
        )


def reconciled(snapshot: ReportSnapshot) -> tuple[DcfInput, Decimal | None]:
    saved = DcfInput.model_validate(snapshot.payload)
    if snapshot.calculation_version != saved.calculation_version:
        raise ValueError("DCF report metadata must match the pinned calculation version")
    price_value = saved.quote.get("price")
    price: Decimal | None = TypeAdapter(Decimal | None).validate_python(price_value)
    reproduced = dcf_scenarios(saved.base_statement, saved.parameters, price)
    expected = TypeAdapter(list[DcfScenarioResult]).validate_python(reproduced["scenarios"])
    if saved.scenarios != expected:
        raise ValueError(
            "Saved DCF does not reconcile to its pinned inputs and calculation version"
        )
    return saved, price


def model_sheets(snapshot: ReportSnapshot) -> list[ModelSheet]:
    saved, price = reconciled(snapshot)
    source = ModelSheet("DCF Inputs", last_column=5)
    source.write("A1", snapshot.title, "header")
    for row, (key, text_value) in enumerate(
        (
            ("Security", saved.parameters.symbol),
            (
                "Currency / monetary unit",
                snapshot.currency + " / " + str(snapshot.payload.get("unit", "Not recorded")),
            ),
            ("Source / state", snapshot.source + " / " + snapshot.quality),
            ("Calculation version", snapshot.calculation_version),
        ),
        2,
    ):
        source.write(f"A{row}", key)
        source.write(f"B{row}", text_value, "source")
    for row, key in enumerate(("revenue", "debt", "cash", "shares"), 7):
        source.write(f"A{row}", key.title())
        base_value = TypeAdapter(Decimal).validate_python(saved.base_statement[key])
        source.write(f"B{row}", float(base_value), "source")
    source.write("A11", "Reference price")
    source.write("B11", float(price) if price is not None else None, "source")
    source.write("A12", "Initial working capital override")
    wc = saved.parameters.initial_working_capital
    source.write("B12", float(wc) if wc is not None else None, "input")
    source.write("A14", "End-year FCFF; no immediate tax credit on operating losses.")
    source.write(
        "A15", "Inputs blue; source values green; formulas black. Amounts retain source units."
    )
    source.write("A16", "#N/A indicates invalid assumptions or an unavailable reference value.")
    sheets = [source]
    if saved.parameters.wacc_inputs is not None:
        sheets.append(wacc_sheet(saved.parameters))
    summary = ModelSheet("DCF Summary")
    for column, label in zip(
        "ABCDEFGH",
        (
            "Scenario",
            "Fair value",
            "Enterprise value",
            "Equity value",
            "Upside",
            "Terminal share",
            "Saved fair value",
            "Difference",
        ),
        strict=True,
    ):
        summary.write(column + "1", label, "header")
    for index, result in enumerate(saved.scenarios, 2):
        sheets.append(scenario_sheet(saved, result, price))
        sheets.append(sensitivity_sheet(result))
        name = f"'DCF {result.name}'"
        summary.write(f"A{index}", result.name)
        for column, row, value, percent in (
            ("B", 31, result.fair_value, False),
            ("C", 26, result.enterprise_value, False),
            ("D", 29, result.equity_value, False),
            ("E", 33, result.upside, True),
            ("F", 34, result.terminal_share, True),
        ):
            summary.formula(f"{column}{index}", f"={name}!B{row}", value, percent)
        summary.write(f"G{index}", float(result.fair_value), "source")
        summary.formula(f"H{index}", f"=B{index}-G{index}", Decimal(0))
    summary.write("A7", "Differences reflect changes from the immutable saved valuation.")
    summary.write("A8", snapshot.disclosure)
    return [summary, *sheets]


def scenario_sheet(saved: DcfInput, result: DcfScenarioResult, price: Decimal | None) -> ModelSheet:
    sheet = ModelSheet(f"DCF {result.name}", last_column=max(7, len(result.forecast) + 1))
    assumption = result.assumptions
    sheet.write("A1", result.name + " | Unlevered FCFF", "header")
    for address, label, value, percent in (
        ("B5", "Tax", assumption.tax_rate, True),
        ("D5", "D&A / revenue", assumption.depreciation_pct, True),
        ("F5", "Capex / revenue", assumption.capex_pct, True),
        ("H5", "Working capital / revenue", assumption.working_capital_pct, True),
        ("B6", "WACC", assumption.wacc, True),
        ("D6", "Terminal growth", assumption.terminal_growth, True),
        ("F6", "Exit EBITDA multiple", assumption.exit_multiple, False),
    ):
        sheet.write(chr(ord(address[0]) - 1) + address[1:], label)
        sheet.write(address, float(value), "input", percent)
    sheet.write("G6", "Terminal method")
    sheet.write("H6", assumption.terminal_method, "input")
    sheet.write("A8", "Forecast year", "header")
    sheet.write("B8", "Base", "header")
    labels = (
        "Revenue growth",
        "Revenue",
        "EBIT margin",
        "EBIT",
        "Cash taxes",
        "NOPAT",
        "Depreciation",
        "Capital expenditure",
        "Working capital",
        "Change in working capital",
        "FCFF",
        "Discount factor",
        "Present value of FCFF",
    )
    for row, label in enumerate(labels, 9):
        sheet.write(f"A{row}", label)
    revenue = Decimal(str(saved.base_statement["revenue"]))
    wc = saved.parameters.initial_working_capital
    sheet.formula("B10", "='DCF Inputs'!B7", revenue)
    sheet.formula(
        "B17",
        "=IF(ISNUMBER('DCF Inputs'!B12),'DCF Inputs'!B12,B10*$H$5)",
        wc if wc is not None else revenue * assumption.working_capital_pct,
    )
    for column, forecast in enumerate(result.forecast, 2):
        letter, previous = chr(65 + column), chr(64 + column)
        sheet.write(letter + "8", forecast["year"], "header")
        sheet.write(letter + "9", float(forecast["growth"]), "input", True)
        sheet.write(letter + "11", float(forecast["ebit_margin"]), "input", True)
        forecast_values: Mapping[str, object] = forecast
        for number, expression, key in (
            (10, f"{previous}10*(1+{letter}9)", "revenue"),
            (12, f"{letter}10*{letter}11", "ebit"),
            (13, f"MAX(0,{letter}12)*$B$5", "tax"),
            (14, f"{letter}12-{letter}13", "nopat"),
            (15, f"{letter}10*$D$5", "depreciation"),
            (16, f"{letter}10*$F$5", "capex"),
            (17, f"{letter}10*$H$5", "working_capital"),
            (18, f"{letter}17-{previous}17", "delta_working_capital"),
            (19, f"{letter}14+{letter}15-{letter}16-{letter}18", "fcff"),
            (21, f"{letter}19*{letter}20", "present_value"),
        ):
            forecast_value = TypeAdapter(Decimal).validate_python(forecast_values[key])
            sheet.formula(f"{letter}{number}", "=" + expression, forecast_value)
        sheet.formula(
            letter + "20",
            f"=IF($B$6>0,1/(1+$B$6)^{letter}$8,NA())",
            Decimal(1) / (1 + assumption.wacc) ** forecast["year"],
        )
    last = chr(66 + len(result.forecast))
    for row, label in enumerate(
        (
            "Terminal value",
            "PV of terminal value",
            "Enterprise value",
            "Debt",
            "Cash",
            "Equity value",
            "Shares",
            "Fair value per share",
            "Reference price",
            "Upside",
            "Terminal share of EV",
        ),
        24,
    ):
        sheet.write(f"A{row}", label)
    terminal = f'IF($H$6="PERPETUITY",IF(AND($B$6>$D$6,$B$6>0),{last}19*(1+$D$6)/($B$6-$D$6),NA()),IF(AND($H$6="EXIT_MULTIPLE",$F$6>0),({last}12+{last}15)*$F$6,NA()))'
    for address, expression, summary_value, percent in (
        ("B24", terminal, result.terminal_value, False),
        ("B25", f"B24*{last}20", result.terminal_pv, False),
        ("B26", f"SUM(C21:{last}21)+B25", result.enterprise_value, False),
        ("B27", "'DCF Inputs'!B8", Decimal(str(saved.base_statement["debt"])), False),
        ("B28", "'DCF Inputs'!B9", Decimal(str(saved.base_statement["cash"])), False),
        ("B29", "B26-B27+B28", result.equity_value, False),
        ("B30", "'DCF Inputs'!B10", result.shares, False),
        ("B31", "IF(B30>0,B29/B30,NA())", result.fair_value, False),
        ("B32", "IF(ISNUMBER('DCF Inputs'!B11),'DCF Inputs'!B11,NA())", price, False),
        ("B33", "IF(AND(ISNUMBER(B32),B32>0),B31/B32-1,NA())", result.upside, True),
        ("B34", "IF(B26>0,B25/B26,NA())", result.terminal_share, True),
    ):
        sheet.formula(address, "=" + expression, summary_value, percent)
    if saved.parameters.apply_calculated_wacc:
        sheet.cells = [cell for cell in sheet.cells if cell.address != "B6"]
        sheet.formula("B6", "='DCF WACC'!B15", assumption.wacc, True)
    return sheet


def wacc_sheet(request: DcfRequest) -> ModelSheet:
    inputs = request.wacc_inputs
    if inputs is None:
        raise ValueError("WACC worksheet requires explicit market inputs")
    sheet = ModelSheet("DCF WACC", last_column=3)
    sheet.write("A1", "Market-weighted WACC", "header")
    for row, (label, value, percent) in enumerate(
        (
            ("Risk-free rate", inputs.risk_free, True),
            ("Beta", inputs.beta, False),
            ("Equity risk premium", inputs.equity_risk_premium, True),
            ("Pre-tax cost of debt", inputs.cost_of_debt, True),
            ("Tax rate", inputs.tax_rate, True),
            ("Equity market value", inputs.equity_market_value, False),
            ("Debt market value", inputs.debt_market_value, False),
        ),
        3,
    ):
        sheet.write(f"A{row}", label)
        sheet.write(f"B{row}", float(value), "input", percent)
    result = calculate_wacc(inputs)
    for row, label, expression, key in (
        (11, "Cost of equity", "B3+B4*B5", "cost_of_equity"),
        (12, "After-tax cost of debt", "B6*(1-B7)", "after_tax_cost_of_debt"),
        (13, "Equity weight", "IF(SUM(B8:B9)>0,B8/SUM(B8:B9),NA())", "equity_weight"),
        (14, "Debt weight", "1-B13", "debt_weight"),
        (15, "WACC", "B13*B11+B14*B12", "wacc"),
    ):
        sheet.write(f"A{row}", label)
        values: Mapping[str, object] = result
        sheet.formula(
            f"B{row}", "=" + expression, TypeAdapter(Decimal).validate_python(values[key]), True
        )
    return sheet


def sensitivity_sheet(result: DcfScenarioResult) -> ModelSheet:
    sheet = ModelSheet(f"DCF {result.name} Sens", last_column=3)
    sheet.write("A1", "Perpetuity sensitivities", "header")
    for column, label in zip("ABC", ("WACC", "Terminal growth", "Fair value"), strict=True):
        sheet.write(column + "2", label, "header")
    name = f"'DCF {result.name}'"
    last = chr(66 + len(result.forecast))
    for start, cases, exit_method in (
        (3, result.growth_sensitivity, False),
        (31, result.exit_sensitivity, True),
    ):
        for index, case in enumerate(cases, start):
            sheet.formula(
                f"A{index}",
                f"={name}!$B$6+({case.wacc - result.assumptions.wacc})",
                case.wacc,
                True,
            )
            axis = case.exit_multiple if exit_method else case.terminal_growth
            if axis is None:
                raise ValueError("Missing sensitivity axis")
            base = (
                result.assumptions.exit_multiple
                if exit_method
                else result.assumptions.terminal_growth
            )
            cell = "F6" if exit_method else "D6"
            sheet.formula(
                f"B{index}", f"={name}!${cell[0]}${cell[1:]}+({axis - base})", axis, not exit_method
            )
            terminal = (
                f"({name}!{last}12+{name}!{last}15)*B{index}"
                if exit_method
                else f"{name}!{last}19*(1+B{index})/(A{index}-B{index})"
            )
            valid = f"AND(A{index}>0,{name}!$B$30>0" + (
                f",B{index}>0)" if exit_method else f",B{index}<A{index})"
            )
            expression = f"=IF({valid},(SUMPRODUCT({name}!C19:{last}19/(1+A{index})^{name}!C8:{last}8)+({terminal})/(1+A{index})^{len(result.forecast)}-{name}!$B$27+{name}!$B$28)/{name}!$B$30,NA())"
            sheet.formula(f"C{index}", expression, case.fair_value)
    sheet.write("A29", "Exit-multiple sensitivities", "header")
    for column, label in zip("ABC", ("WACC", "EBITDA multiple", "Fair value"), strict=True):
        sheet.write(column + "30", label, "header")
    return sheet
