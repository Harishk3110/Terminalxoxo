# Private Reporting Readiness

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
The mandated artifact authoring runtime is unavailable in this session. Approval
to extend the repository's existing export libraries was requested and has not
been received. Existing exports are not represented as those finished deliverables.

Pine generation and user-export comparison are implemented separately; see
TRADINGVIEW_STUDIO.md. Broker connectivity remains read-only.
