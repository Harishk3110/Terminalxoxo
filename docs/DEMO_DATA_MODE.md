# Demo Data Mode

local-demo works without credentials. Existing database seeding is retained: 20 instruments, daily/intraday bars, 17 macro series, reference ledger and supporting research/strategy/operations fixtures. Fundamentals are deterministic synthetic annual statements, persisted on first request, clearly labelled and never described as filed financials.

Core risk derives current-weight returns from aligned persisted daily closes. Portfolio performance replays recorded cash flows and holdings through historical closes, including fully sold securities. These replace the fixed-return shortcuts on the terminal's active performance/risk APIs.

Important: the inherited transaction prices and synthetic price histories are independent fixtures. Reference capital is SGD 70,000; NAV is calculated and is not forced to match it. The resulting performance can be unrealistic and is explicitly not investment performance. Prices can predate a new manual transaction; historical performance stops at the last available close.

Backtesting uses backtesting.py 0.6.5, a long-only moving-average template, next-open execution, editable cash/fees/spread and persisted curves/trades. Uploaded close-only files use the close as missing OHLC values; survivorship, liquidity and financing are not modelled. Arbitrary editor text is downloadable research only and is not executed.

FRED remains NOT_CONFIGURED without credentials; no live market, news, options or broker connection is fabricated. Out-of-demo private API requests require a valid session, but this is not a production security certification: encrypted secret storage, CSRF/rate-limit hardening, per-user isolation and TOTP lifecycle still need work.

Technical references: [backtesting.py](https://github.com/kernc/backtesting.py), [TanStack Virtual](https://tanstack.com/virtual/latest/docs/framework/react/react-virtual).
