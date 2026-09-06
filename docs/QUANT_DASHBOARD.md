# Quant Dashboard

Route /quant-dashboard shows versioned strategy definitions and persisted
analytical jobs. The implemented execution template is long-only moving-average
crossover using backtesting.py; other definitions remain research definitions.
No arbitrary user code, verified live signal stream or fabricated paper
performance is provided.

Backtests use next-open fills, explicit commission/spread, selected dates,
capital and MA windows. Approved imported OHLC datasets are pinned by version;
close-only imports are rejected for these new curated backtests. Survivorship,
financing, liquidity and corporate-action adjustment are not modeled.

Factor Lab uses source-aware trailing momentum and cross-sectional ranks.
Historical rank IC and equal-count quintile forward returns are computed when
coverage permits. A fixed chronological 70/30 IS/OOS split purges the forward
horizon at its boundary. Each segment needs ten observations for IC summaries.
Overlapping forward returns make the unannualized IC IR a descriptive ratio,
not a significance test or validated edge. There is no model fitting,
walk-forward optimization or multiple-testing correction.

Route /edge-lab records a hypothesis against an immutable dataset version.
Gates are explicit and incomplete until reviewed; automatic promotion to paper
or live trading is disabled. Candidate review can retain, reject or archive.
