# TradingView Studio

Implemented endpoint:

`GET /api/v1/pine/export?strategy_type=moving_average_crossover`

## Supported

- Pine Script v5 generation for moving-average crossover.
- Long-only strategy.
- Commission input.
- Slippage input.
- Date filter.
- Alert condition.
- Compatibility response `SUPPORTED`.

## Partially Supported

Other strategy types return `PARTIALLY_SUPPORTED` with an explanatory reason.

## Not Supported

- Automatic TradingView deployment.
- Broker execution.
- Webhook-to-order routing.

Generated Pine source is for manual TradingView import only.
