# TradingView Studio

Private `/tradingview` generates saved Pine v6 SMA, RSI, MACD and closing-price
breakout templates. Parameters include windows, direction, date/session limits,
commission percentage, slippage ticks, allocation and fixed/profit/trailing exits.
Fixed and trailing stops are mutually exclusive. Dates use UTC; sessions use the
exchange timezone. Existing positions are not flattened at session end.

Download the `.pine` source, open TradingView Pine Editor, paste it, save and add
it to a chart. Compilation is explicitly **UNVERIFIED** in KnK. Review Strategy
Properties and chart currency/session/adjustment settings. Any simulated strategy
orders exist only in TradingView's emulator. KnK has no broker execution or
automatic TradingView deployment. Alerts use `alert()` and emulator fill messages.

Export chart data with `time`, `close`, `KNK_SIGNAL` and upload the CSV against the
saved template. Time must be timezone-aware ISO or Unix seconds. Up to 50,000
unique chronological bars/10 MB are accepted. KnK recomputes indicator direction
with the existing backtest signal engine using those supplied closes. Counts
exclude reported warm-up and missing signals; full counts and up to 500 detail
rows are saved with original-file hash, object key, template hash and settings.
The external CSV is user-provided, not independently authenticated market data.

This comparison does not establish fill, stop, fee, session, FX or P&L equivalence.
RSI uses different Wilder/EWM initialization; MACD warm-up histories can differ.
SMA/MACD templates follow signal direction with no pyramiding. RSI and breakout
flatten when neutral. Breakout uses prior closing extrema, not intrabar ranges.
Protective orders first become available at the close after an entry fill.

Compatibility is PARTIALLY_SUPPORTED. Arbitrary Python models, webhook execution,
automated compiler certification and complete trade reconciliation are unsupported.

Primary references:
- [TradingView strategies](https://www.tradingview.com/pine-script-docs/concepts/strategies/)
- [TradingView alerts](https://www.tradingview.com/pine-script-docs/concepts/alerts/)
- [TradingView sessions](https://www.tradingview.com/pine-script-docs/concepts/sessions/)
