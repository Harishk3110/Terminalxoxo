# Backtesting Methodology

Backtests must record dataset version, rebalance timing, fees, slippage, corporate actions, FX assumptions, benchmark, constraints, and look-ahead prevention checks.

Long-running runs belong in `services/worker-quant` and stream progress through job events.
