# Private Reporting Readiness

## Overnight Pipeline, 2026-09-12

Active Compose reports now use `app.report_engine` from the API image. The old
standalone entrypoint stays disabled, not a second unauthenticated renderer.
`/api/v1/report-jobs` provides owned submission/list/detail/source/download routes.
Private outputs use a separate prefix and atomic create-only writes, with no
public URL or legacy manifest alias. SQL claims are conditional; an expired worker
cannot publish. Source/output tampering fails closed, with sanitized errors/audits.
Downloads expire after 30 days; physical object purging is not scheduled yet.

Review exports: portfolio/risk/equity XLSX/PPTX/PDF; backtest XLSX/PDF;
factor/macro/DCF/comparables XLSX; quant PPTX. Unabridged immutable inputs remain
in the authenticated JSON source download. PDF/PPTX abbreviate long table text
with ellipses and explicitly reference that source. Missing inputs stay unavailable.
Position XLSX formulas include multiplier/FX and tested caches; curve charts use
pinned values. DCF exports now have source-reconciled native forecast, WACC,
terminal-value, equity-bridge and sensitivity formulas, with independent Excel
recalculation tests; see DCF_WORKBOOK_VALIDATION.md. Other families remain review
exports, not complete editable financial models or an IC narrative certification.

Browser generation/download passed, with inspected desktop/mobile screenshots.
Isolated PostgreSQL/MinIO file/hash/persistence and anonymous rejection passed.
Complete financial-model/deck content and rendered-artifact review remain partial.
The PDF adapter pins [ReportLab 4.4.10](https://pypi.org/project/reportlab/4.4.10/).
ReportLab development stubs are pinned; XlsxWriter has one documented adapter-local
missing-stub import ignore, not a module-wide type exclusion.

## Earlier Baseline

Existing authenticated portfolio, risk, macro and saved-analysis XLSX exports
remain available. Saved-run exports tolerate absent source timestamps and align
heterogeneous result columns by key. Missing timestamps remain empty, not invented.
Position formulas include contract multipliers. Export manifests retain the actual
source quality instead of labeling every output DEMO; downloads verify known hashes.

The separate report-engine service previously generated hardcoded demo holdings
and allowed unauthenticated downloads. These endpoints now reject access; its
readiness probe returns 503. Existing exports are generated within the private API.

The requested complete formula-driven equity/quant/portfolio workbook families,
26-section IC decks, PPTX/PDF conversion and PNG chart packages are **not complete**.
The 2026-09-11 final master directive explicitly permits XlsxWriter/OpenPyXL and
python-pptx/PptxGenJS with appropriate PDF/chart libraries. The earlier alternate
engine approval blocker is therefore superseded. Implementation and verification
of the isolated report worker and full workbook/deck/PDF families are still
outstanding. Existing exports are not represented as those finished deliverables.

Pine generation and user-export comparison are implemented separately; see
TRADINGVIEW_STUDIO.md. Broker connectivity remains read-only.
