# Native DCF Workbook

The owned `dcf` / `xlsx` report job renders a formula-driven workbook from its
immutable `knk-fcff-1.0` snapshot. The worker first reproduces the saved scenario
results from the pinned statement, overrides, quote and request. A mismatched
forecast, valuation, sensitivity or calculation-version label fails the job.
It does not query current prices or substitute demo financial statements.

The workbook includes:

- A scenario summary with fair value, enterprise/equity value, upside, terminal
  contribution and differences from the immutable saved fair values.
- Source statement inputs, units, price and explicit initial working capital.
- One to ten forecast years, revenue growth/margins, cash taxes, NOPAT, D&A,
  capex, working-capital changes, FCFF and end-year discount factors.
- Perpetuity and exit-EBITDA terminal methods, discounted terminal value and
  the debt/cash/share bridge to per-share value.
- Market-weighted WACC formulas, linked into scenarios when the saved request
  explicitly applied calculated WACC.
- Twenty-five perpetuity and nine exit-multiple sensitivity formulas per scenario.
- Source lineage, calculation version, dates, source state and internal disclosure.

Inputs are blue, source values green and formulas black. Monetary values retain
the source unit; amounts and share counts must use consistent scales. Display
rounding does not round the underlying formula inputs. Missing reference prices,
invalid perpetuity assumptions and undefined ratios produce `#N/A`, not zero.
Negative enterprise/equity values are retained. Source text cannot become a formula
or external link. Existing model limits still apply, including no automatic NOL
benefit, dilution, minority interest or non-operating adjustments.

## Verification

`tests/sprint/test_dcf_workbook.py` checks formulas, cached values, source integrity,
version mismatch, missing prices, native sensitivities and linked WACC. The report
queue test creates a real saved DCF analysis, generates the job and downloads the
owned formula workbook. All sixteen report-kind/format combinations still have
file-generation coverage; that does not certify every other family's model depth.

The optional Windows Excel integration requires installed Excel and explicit opt-in:

```powershell
$env:KNK_EXCEL_INTEGRATION='1'
.venv-sprint/Scripts/python.exe -m pytest tests/integration/test_excel_dcf.py -q -s
```

Each test creates fictional workbooks under `logs/dcf-validation/<unique-id>`.
An independent hidden Excel instance performs `CalculateFullRebuild`, saves a new
recalculated workbook and exports PDF. Every formula cache is compared at relative
and absolute tolerance `1e-10`. Tests also change revenue and create an invalid
WACC/growth combination, then verify the downstream Excel results. Sources are
never overwritten. A missing Excel installation is not represented as a pass.

The PowerShell adapter rejects existing output directories and active/external
workbook content. It disables VBA and events and opens without updating links.
See Microsoft's [Workbooks.Open](https://learn.microsoft.com/en-us/office/vba/api/excel.workbooks.open)
and [AutomationSecurity](https://learn.microsoft.com/en-us/office/vba/api/excel.application.automationsecurity)
contracts. This is a local validation utility, not a server-side Office dependency.

PDF previews use the pinned development-only PDFium renderer. After creating an
output directory, run:

```powershell
.venv-sprint/Scripts/python.exe -m pypdfium2_cli render <rendered.pdf> --output <existing-directory> --scale 1.3 --linear
```

Generated XLSX, PDF and page images remain ignored local evidence, not repository
assets or a public download. Rendering a workbook does not certify an investment
recommendation or complete the remaining equity/quant/deck report families.
