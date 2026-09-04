# Excel Exports

The API generates actual `.xlsx` workbooks through `ReportService` and writes them to object storage.

Implemented endpoints:

- `POST /api/v1/reports/portfolio-xlsx`
- `POST /api/v1/reports/risk-xlsx`
- `POST /api/v1/reports/backtest-xlsx`
- `POST /api/v1/reports/macro-xlsx`
- `GET /api/v1/reports/{report_id}`
- `GET /api/v1/reports/{report_id}/download`

## Implemented Workbook Families

Portfolio workbook sheets:

`Overview`, `Holdings`, `Transactions`, `Cash`, `NAV`, `Performance`, `Exposure`, `Risk`, `Stress`, `Hedge`, `Sources`, `Checks`.

Risk workbook sheets:

`Risk`, `Stress`, `Hedge`, `Sources`, `Checks`.

Backtest workbook sheets:

`Summary`, `Parameters`, `Equity Curve`, `Drawdown`, `Monthly Returns`, `Trades`, `Positions`, `Exposure`, `Fees`, `Data Sources`, `Checks`.

Macro workbook sheets:

`Macro Dashboard`, `Observations`, `Sources`, `Checks`.

Workbooks use frozen panes, number formats, source/quality rows, and XlsxWriter `strings_to_formulas=false` with additional string prefixing for formula-injection-sensitive values.
