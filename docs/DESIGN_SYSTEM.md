# Terminal Design System

Tokens are defined in apps/terminal-web/app/globals.css. Chart colors are centralized in components/ui.tsx.

| Role | Color |
| --- | --- |
| Background | #000000 |
| Panels | #0A0A0A, #111111 |
| Borders | #2B2B2B, #1D1D1D |
| Text | #F2F2F2, #A8A8A8, #686868 |
| Brand / assumptions | #FF9D00 |
| Warning / demo | #FFD400 |
| Action / benchmark | #25B7E9 |
| Positive / negative | #00C875 / #FF4D4F |
| Calculated | #B28DFF |

Body text is 12px; headings within panels are 11px. Numbers use tabular monospace. Tables use 28px rows, right-aligned numeric columns, internal scrolling and sparse horizontal rules. Panels have square corners, 27px headers and provenance footers. Input/button heights are 28px; icon tools are 24px with accessible labels and tooltips. Keyboard focus is white.

Mobile monitoring uses stacked analytical panels and a two-column KPI grid; the inspector is initially closed. Main content scrolls internally without expanding the outer viewport.

ECharts uses a black plot, restrained grid, amber primary series and blue benchmark. Missing values are gaps, not zero. Price charts support range selection, internal zoom, legends, crosshair tooltips and PNG export.

Shared components: Panel, DataTable, Kpis, Chart, LineChart, Badge, IconButton, Field, Empty. DataTable uses TanStack Table and TanStack Virtual, column resizing/reordering, multi-sort, filtering, saved views, optional first-column pinning, keyboard cell navigation/copy and CSV export. Symbol rows expose a context menu. Panels support refresh when supplied, export when rows exist, source details and expansion.

Limitations: saved views are browser-local; only the first column can be pinned; complex panel docking and per-table XLSX exports are not implemented.
