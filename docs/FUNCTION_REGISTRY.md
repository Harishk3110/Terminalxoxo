# Function Registry

Canonical source: services/api/app/data/functions.json. The API, palette, rail and typed @knk/terminal-functions package consume this same file. There are 110 registered functions and 96 distinct registry route patterns.

Statuses: available = operational workflow; demo_available = working calculation/view with synthetic inputs; provider_required = missing external data/connection; in_development = not implemented. Registry membership is not a claim that every specialist feature is complete. Shared analytical routes intentionally serve related functions.

| Function | Name | Status | Route |
| --- | --- | --- | --- |
| HOME | Portfolio Command Centre | demo_available | /overview |
| Q | Quote | demo_available | /quote/{instrumentId} |
| GP | Price Chart | demo_available | /chart/{instrumentId} |
| TECH | Technical Analysis | demo_available | /technicals/{instrumentId} |
| BREADTH | Market Breadth | demo_available | /markets |
| HEAT | Heatmap | demo_available | /heatmap |
| SECTOR | Sector Monitor | demo_available | /sectors |
| DES | Security Description | demo_available | /security/{instrumentId} |
| FIN | Financial Statements | demo_available | /financials/{instrumentId} |
| VAL | Valuation | demo_available | /valuation/{instrumentId} |
| DCF | Discounted Cash Flow | demo_available | /dcf/{instrumentId} |
| WACC | Weighted Average Cost of Capital | in_development | /functions/wacc |
| COMP | Comparable Companies | demo_available | /comparables/{instrumentId} |
| EST | Analyst Estimates | provider_required | /functions/est |
| EARN | Earnings | provider_required | /functions/earn |
| SCREEN | Equity Screener | demo_available | /security-master |
| RELVAL | Relative Valuation | demo_available | /comparables/{instrumentId} |
| OWN | Ownership | provider_required | /functions/own |
| SHORT | Short Interest | provider_required | /functions/short |
| DIV | Dividends | provider_required | /functions/div |
| CA | Corporate Actions | provider_required | /functions/ca |
| OPT | Options Chain | provider_required | /functions/opt |
| DELTA | Delta | provider_required | /functions/delta |
| GAMMA | Gamma | provider_required | /functions/gamma |
| THETA | Theta | provider_required | /functions/theta |
| VEGA | Vega | provider_required | /functions/vega |
| RHO | Rho | provider_required | /functions/rho |
| GREEKS | Option Greeks | provider_required | /functions/greeks |
| ADV GREEKS | Advanced Greeks | provider_required | /functions/adv-greeks |
| GEX | Gamma Exposure | provider_required | /functions/gex |
| DEX | Delta Exposure | provider_required | /functions/dex |
| IV | Implied Volatility | provider_required | /functions/iv |
| IVS | Volatility Surface | provider_required | /functions/ivs |
| SKEW | Volatility Skew | provider_required | /functions/skew |
| PCR | Put/Call Ratio | provider_required | /functions/pcr |
| MAXPAIN | Max Pain | provider_required | /functions/maxpain |
| OIFLOW | Options Flow | provider_required | /functions/oiflow |
| PAYOFF | Payoff Analysis | provider_required | /functions/payoff |
| OPTSTRAT | Options Strategy Builder | provider_required | /functions/optstrat |
| EMOVE | Expected Move | provider_required | /functions/emove |
| VOLCONE | Volatility Cone | provider_required | /functions/volcone |
| MACRO | Macro Dashboard | demo_available | /macro |
| CAL | Economic Calendar | provider_required | /functions/cal |
| CB | Central Banks | provider_required | /functions/cb |
| CURVE | Yield Curves | demo_available | /macro |
| BONDS | Bond Monitor | provider_required | /functions/bonds |
| RATES | Rates Monitor | demo_available | /macro |
| CREDIT | Credit Spreads | demo_available | /macro |
| DURATION | Duration Analysis | provider_required | /functions/duration |
| FX | FX Monitor | provider_required | /functions/fx |
| CARRY | FX Carry | provider_required | /functions/carry |
| FXVOL | FX Volatility | provider_required | /functions/fxvol |
| CRYPTO | Crypto Monitor | provider_required | /functions/crypto |
| PORT | Portfolio | demo_available | /portfolio |
| POSITIONS | Positions | demo_available | /positions |
| PERF | Performance | demo_available | /performance |
| ATTR | Attribution | in_development | /functions/attr |
| RISK | Portfolio Risk | demo_available | /risk |
| VAR | Value at Risk | demo_available | /risk |
| STRESS | Stress Testing | demo_available | /stress-tests |
| PORT GREEKS | Portfolio Greeks | provider_required | /functions/port-greeks |
| HEDGE | Hedge Recommendations | demo_available | /hedge |
| REBAL | Rebalance Recommendations | provider_required | /functions/rebal |
| QUANT | Quant Lab | demo_available | /quant |
| BACKTEST | Backtesting | demo_available | /backtests |
| SIGNAL | Signal Engine | in_development | /functions/signal |
| CORR | Correlation | demo_available | /risk |
| BETA | Beta | demo_available | /risk |
| FACTOR | Factor Lab | demo_available | /factor-lab |
| PAIR | Pair Analysis | in_development | /functions/pair |
| REG | Regression | in_development | /functions/reg |
| STATS | Statistics | demo_available | /factor-lab |
| WALK | Walk-Forward Analysis | in_development | /functions/walk |
| MC | Monte Carlo | in_development | /functions/mc |
| EDGE | Edge Lab | available | /edge-lab |
| MODEL | Model Lab | in_development | /functions/model |
| RESEARCH | Research Workspace | available | /research |
| THESIS | Investment Thesis | available | /thesis |
| IDEA | Idea Tracker | available | /ideas |
| NEWS | News | provider_required | /functions/news |
| SENT | Sentiment | provider_required | /functions/sent |
| FILINGS | Regulatory Filings | provider_required | /functions/filings |
| TRANSCRIPTS | Earnings Transcripts | provider_required | /functions/transcripts |
| DATA | Data Explorer | available | /data-catalogue |
| DROP | Data Drop | available | /data-drop |
| CATALOGUE | Data Catalogue | available | /data-catalogue |
| JOBS | Data Jobs | available | /data-jobs |
| API | API Monitor | available | /api-monitor |
| EXCEL | Excel Studio | available | /excel-studio |
| DECK | Deck Builder | in_development | /functions/deck |
| PDF | PDF Reports | in_development | /functions/pdf |
| PINE | Pine Script Studio | available | /tradingview |
| TV ALERTS | TradingView Alert Inbox | in_development | /functions/tv-alerts |
| WATCH | Watchlists | available | /watchlists |
| ALERT | Alerts | available | /alerts |
| HEALTH | System Health | available | /system-health |
| RECON | Reconciliation | provider_required | /reconciliation |
| SETTINGS | Settings | available | /settings/connections |
| CONN | Connections | available | /settings/connections |
| SECURITY | Security Settings | available | /settings/security |
| FUNC | Function Directory | available | /functions |
| AI | KnK AI | provider_required | /functions/ai |
| NAV | Portfolio NAV | available | /overview |
| PNL | Portfolio P&L | available | /performance |
| TRADES | Trade Monitor | available | /trade-monitor |
| RISKMON | Risk & Trade Monitor | available | /risk-trade-monitor |
| QMON | Quant Research Monitor | available | /quant-dashboard |
| EQUITY | Equity Research Desk | available | /equity |
| KOYFIN | Koyfin File Drop | available | /data-drop |
| DATADROP | External Data Drop | available | /data-drop |

TECH currently supports SMA20/SMA50; no indicator builder. BREADTH/SECTOR are basic market inspection views. THESIS/IDEA retain private free-form notes. FACTOR/STATS include trailing momentum ranks, historical rank IC and quintile forward returns with a purged IS/OOS split; this is not walk-forward validation or proven edge. EDGE records pinned research candidates, with paper promotion gated. HEDGE is an integer ETF beta-exposure estimate, not portfolio optimization. EXCEL supports portfolio, risk, macro and completed backtests; deck/PDF generation is unavailable. PINE exports one approved moving-average template. Broker Monitor supports read-only reported snapshots and explicit recorded-fill approval; actual paper connectivity remains unverified.
