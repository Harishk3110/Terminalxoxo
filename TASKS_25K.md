# TASKS 25K

Baseline: c3d9e847604fbbfb59df170c1b5f83f7dbec94a1. Existing behavior is not credited
as new implementation. Check an item only after implementation, integration,
execution, tests and recorded evidence. Source references refer to the supplied
25K sprint directive; documentation contributes zero qualifying LOC.

## Current Execution

- [x] Verify baseline inventory and LOC-counter regression tests (55 counter tests).
- [x] Verify FIFO/policy, persisted lots, settlement, corrections and accounting subledgers (checkpoint evidence in docs/BUILD_EVIDENCE_25K.md).
- [x] Verify historical component queries, balance reversals, saved-data copy preservation and desktop/mobile accounting workflows.
- [x] Verify transaction context, replay cash effects, 19-kind entry UI and audit detail views (442 Python / 103 frontend / 18 browser tests; docs/BUILD_EVIDENCE_25K.md).
- [x] Verify cash-based daily position P&L, corporate-action reference transfers, closed-position income and unknown marks (470 Python / 18 browser tests; docs/BUILD_EVIDENCE_25K.md).
- [ ] Complete remaining M1 storage precision, native/base position metrics, exposure detail and portfolio creation UI; verify live migration before certification.
- [ ] Complete M2-M20 and all category LOC/acceptance gates.

## Full Directive Checklist


### KnK CAPITAL TERMINAL


### 25,000+ LINE PRODUCTION IMPLEMENTATION SPRINT


### PORTFOLIO NAV + EQUITY + QUANT + RISK/TRADE + DATA INGESTION

- [ ] [L7] The current visual shell is approved.
- [ ] [L9] Do not redesign the terminal from scratch.
- [ ] [L11] Do not create another repository.
- [ ] [L13] Do not replace the current black/amber institutional interface with a generic SaaS dashboard.
- [ ] [L16] Do not return another scaffold.
- [ ] [L18] Do not stop after creating schemas, routes, page shells, documentation, or placeholder calculations.
- [ ] [L21] Continue working in the current repository, branch, workspace, and existing GitHub remote.
- [ ] [L24] The previous KnK Capital Terminal master specification, portfolio-first addendum, Bloomberg-inspired terminal specification, function registry, and current terminal shell remain binding.
- [ ] [L28] This directive begins a major implementation sprint requiring at least:
- [ ] [L30] 25,000 NEW LINES OF MEANINGFUL NON-GENERATED SOURCE CODE AND TESTS
- [ ] [L32] added after the baseline commit recorded at the start of this task.
- [ ] [L34] The line-count target is mandatory, but it must not be achieved through:
- [ ] [L36] Empty wrappers.
- [ ] [L37] Generated files.
- [ ] [L38] Repeated boilerplate.
- [ ] [L39] Giant fixture files.
- [ ] [L40] Copied data.
- [ ] [L41] Documentation padding.
- [ ] [L42] Comment padding.
- [ ] [L43] Duplicated models.
- [ ] [L44] Fake API routes.
- [ ] [L45] Placeholder React components.
- [ ] [L46] Dead code.
- [ ] [L47] Empty tests.
- [ ] [L48] Tests that assert true.
- [ ] [L49] Repeated CSS.
- [ ] [L50] Generated API clients.
- [ ] [L51] Lockfiles.
- [ ] [L52] Build outputs.
- [ ] [L53] Database dumps.
- [ ] [L54] Coverage reports.
- [ ] [L56] The required code must implement real operating functionality.
- [ ] [L58] The goal is not merely 25,000 lines.
- [ ] [L60] The goal is:
- [ ] [L62] A FUNCTIONAL PRODUCTION-STYLE KNK CAPITAL OPERATING TERMINAL
- [ ] [L64] with a minimum of 25,000 lines of new meaningful implementation and tests supporting the functionality.

### 1. MAIN PRODUCT PURPOSE

- [ ] [L71] The KnK Capital Terminal is primarily an internal proprietary investment operating system for managing the KnK Capital main portfolio.
- [ ] [L74] The main portfolio initially represents:
- [ ] [L76] Portfolio Code:
- [ ] [L77] KNK_MAIN
- [ ] [L79] Portfolio Name: KnK Capital Main Portfolio
- [ ] [L82] Initial Reference Capital: SGD 70,000
- [ ] [L85] Base Currency:
- [ ] [L86] SGD
- [ ] [L88] Timezone: Asia/Singapore
- [ ] [L91] Broker Mode: IBKR Paper Trading
- [ ] [L94] Execution Mode: Manual execution only
- [ ] [L97] External Clients: None
- [ ] [L100] The most important uses of the terminal are:
- [ ] [L102] 1. Track the main portfolio.
- [ ] [L103] 2. Calculate accurate portfolio NAV.
- [ ] [L104] 3. Track cash and multi-currency balances.
- [ ] [L105] 4. Track positions and transactions.
- [ ] [L106] 5. Track realised and unrealised P&L.
- [ ] [L107] 6. Monitor daily, monthly, yearly, and since-inception performance.
- [ ] [L108] 7. Monitor trades entered manually.
- [ ] [L109] 8. Reconcile internal records with IBKR Paper.
- [ ] [L110] 9. Import Koyfin and external CSV/XLSX datasets.
- [ ] [L111] 10. Run equity research.
- [ ] [L112] 11. Run quantitative research.
- [ ] [L113] 12. Run backtests.
- [ ] [L114] 13. Run factor research.
- [ ] [L115] 14. Train and test models.
- [ ] [L116] 15. Search for candidate investment edges.
- [ ] [L117] 16. Calculate portfolio risk.
- [ ] [L118] 17. Run stress tests.
- [ ] [L119] 18. Generate manual hedge recommendations.
- [ ] [L120] 19. Generate manual rebalance recommendations.
- [ ] [L121] 20. Export professional Excel models.
- [ ] [L122] 21. Generate equity-research decks and reports.
- [ ] [L123] 22. Export compatible strategies into TradingView Pine Script.
- [ ] [L124] 23. Monitor all data providers and system infrastructure.
- [ ] [L125] 24. Maintain complete data provenance and audit history.
- [ ] [L127] The terminal must never automatically place, modify, transmit, or cancel a broker order.

### 2. CURRENT DESIGN THAT MUST BE PRESERVED

- [ ] [L134] Preserve the approved terminal shell:
- [ ] [L136] Black terminal background.
- [ ] [L137] Amber KnK Capital brand.
- [ ] [L138] White tabular data.
- [ ] [L139] Green positive values.
- [ ] [L140] Red negative values.
- [ ] [L141] Yellow demo and warning indicators.
- [ ] [L142] Compact global search.
- [ ] [L143] Compact active-security strip.
- [ ] [L144] Compact terminal tabs.
- [ ] [L145] Dense desktop layout.
- [ ] [L146] Bottom system status bar.
- [ ] [L147] Bloomberg-inspired function mnemonics.
- [ ] [L148] Current black/amber visual identity.
- [ ] [L149] Minimal border radius.
- [ ] [L150] Sharp panel borders.
- [ ] [L151] Compact data presentation.
- [ ] [L152] Existing Ctrl+K command workflow.
- [ ] [L154] Do not reintroduce:
- [ ] [L156] Large rounded cards.
- [ ] [L157] Large pastel badges.
- [ ] [L158] Cyan branding.
- [ ] [L159] Large "Terminal" title.
- [ ] [L160] Excessive whitespace.
- [ ] [L161] Mobile stacking on desktop.
- [ ] [L162] Decorative gradients.
- [ ] [L163] Generic admin-dashboard components.
- [ ] [L164] Consumer-finance design.
- [ ] [L165] Static marketing cards inside the private terminal.
- [ ] [L167] Improve the existing shell rather than replacing it.

### 3. BASELINE AND 25K LINE-COUNT CONTROL

- [ ] [L173] Before modifying code:
- [ ] [L175] 1. Run:
- [ ] [L177] git status git branch --show-current git rev-parse HEAD git log --oneline -10
- [ ] [L182] 2. Save the starting commit hash into:
- [ ] [L184] .knk-25k-baseline
- [ ] [L186] 3. Create:
- [ ] [L188] docs/IMPLEMENTATION_25K_BASELINE.md
- [ ] [L190] 4. Record:
- [ ] [L192] Baseline commit.
- [ ] [L193] Branch.
- [ ] [L194] Remote.
- [ ] [L195] Current source line count.
- [ ] [L196] Current test line count.
- [ ] [L197] Existing application routes.
- [ ] [L198] Existing backend endpoints.
- [ ] [L199] Existing tests.
- [ ] [L200] Existing Docker services.
- [ ] [L201] Current incomplete areas.
- [ ] [L203] 5. Create:
- [ ] [L205] scripts/count_25k_delta.py
- [ ] [L207] The script must calculate added non-generated code since the baseline.
- [ ] [L209] Include:
- [ ] [L211] .py
- [ ] [L212] .ts
- [ ] [L213] .tsx
- [ ] [L214] .js
- [ ] [L215] .jsx
- [ ] [L216] .sql
- [ ] [L217] .css
- [ ] [L218] .scss
- [ ] [L219] .sh
- [ ] [L220] .ps1
- [ ] [L222] Exclude:
- [ ] [L224] node_modules
- [ ] [L225] .next
- [ ] [L226] dist
- [ ] [L227] build
- [ ] [L228] coverage
- [ ] [L229] .pytest_cache
- [ ] [L230] .mypy_cache
- [ ] [L231] .ruff_cache
- [ ] [L232] generated
- [ ] [L233] vendor
- [ ] [L234] public generated assets
- [ ] [L235] lockfiles
- [ ] [L236] fixture datasets
- [ ] [L237] screenshots
- [ ] [L238] report outputs
- [ ] [L239] documentation
- [ ] [L240] binaries
- [ ] [L241] database files
- [ ] [L242] minified code
- [ ] [L243] generated API clients
- [ ] [L244] generated schema output
- [ ] [L246] Create these minimum category gates:
- [ ] [L248] BACKEND AND DOMAIN IMPLEMENTATION:
- [ ] [L249] Minimum 9,000 new lines
- [ ] [L251] FRONTEND PRODUCT IMPLEMENTATION:
- [ ] [L252] Minimum 6,000 new lines
- [ ] [L254] WORKERS, AGENTS, REPORTING, AND INFRASTRUCTURE CODE: Minimum 3,000 new lines
- [ ] [L257] SUBSTANTIVE AUTOMATED TESTS:
- [ ] [L258] Minimum 7,000 new lines
- [ ] [L260] TOTAL:
- [ ] [L261] Minimum 25,000 new lines
- [ ] [L263] Documentation does not count toward the 25,000 lines.
- [ ] [L265] Generated files do not count.
- [ ] [L267] Fixture datasets do not count.
- [ ] [L269] Migration code may count only where it contains genuine schema logic, constraints, indexes, and upgrade/downgrade implementation.
- [ ] [L272] No individual source file should exceed 1,200 lines unless there is a documented technical reason.
- [ ] [L275] Prefer modular files between 100 and 500 lines.
- [ ] [L277] Create:
- [ ] [L279] docs/LOC_EVIDENCE_25K.md
- [ ] [L281] At every milestone, record:
- [ ] [L283] Backend lines added.
- [ ] [L284] Frontend lines added.
- [ ] [L285] Worker/agent/report lines added.
- [ ] [L286] Test lines added.
- [ ] [L287] Total.
- [ ] [L288] Count command.
- [ ] [L289] Commit.
- [ ] [L290] Date.
- [ ] [L292] Do not report completion until:
- [ ] [L294] scripts/count_25k_delta.py
- [ ] [L296] shows at least 25,000 qualifying new lines and all critical acceptance tests pass.

### 4. REQUIRED CODE QUALITY

- [ ] [L303] Every new module must be:
- [ ] [L305] Typed.
- [ ] [L306] Tested.
- [ ] [L307] Modular.
- [ ] [L308] Documented through concise docstrings where useful.
- [ ] [L309] Integrated into the actual application.
- [ ] [L310] Reachable from an API, worker, terminal page, report, or test.
- [ ] [L311] Free from dead imports.
- [ ] [L312] Free from obvious duplication.
- [ ] [L313] Free from hardcoded fake financial output.
- [ ] [L314] Free from hidden broker execution capability.
- [ ] [L316] Use:
- [ ] [L318] Python:
- [ ] [L319] Ruff.
- [ ] [L320] mypy.
- [ ] [L321] pytest.
- [ ] [L322] Hypothesis where appropriate.
- [ ] [L323] Pydantic.
- [ ] [L324] SQLAlchemy 2.
- [ ] [L325] Decimal.
- [ ] [L326] Polars or pandas where appropriate.
- [ ] [L327] NumPy.
- [ ] [L328] SciPy.
- [ ] [L329] statsmodels.
- [ ] [L330] CVXPY.
- [ ] [L331] DuckDB.
- [ ] [L332] PyArrow.
- [ ] [L334] TypeScript:
- [ ] [L335] Strict mode.
- [ ] [L336] ESLint.
- [ ] [L337] Vitest.
- [ ] [L338] React Testing Library.
- [ ] [L339] Playwright.
- [ ] [L340] TanStack Query.
- [ ] [L341] TanStack Table.
- [ ] [L342] Zod.
- [ ] [L343] React Hook Form.
- [ ] [L344] ECharts or approved charting library.
- [ ] [L346] Do not place financial calculations inside React components.
- [ ] [L348] Do not place financial calculations directly inside API route handlers.
- [ ] [L350] Use:
- [ ] [L352] Route -> Application Service -> Domain Service -> Repository -> Database

### 5. IMPLEMENTATION TRACKING

- [ ] [L362] Create:
- [ ] [L364] TASKS_25K.md
- [ ] [L365] STATUS_25K.md
- [ ] [L366] docs/ACCEPTANCE_25K.md
- [ ] [L367] docs/GAP_AUDIT_25K.md
- [ ] [L368] docs/BUILD_EVIDENCE_25K.md
- [ ] [L370] TASKS_25K.md must contain every implementation requirement in this
- [ ] [L371] directive as checkboxes.
- [ ] [L373] STATUS_25K.md must include:
- [ ] [L375] Current milestone.
- [ ] [L376] Current commit.
- [ ] [L377] Lines added by category.
- [ ] [L378] Services running.
- [ ] [L379] Routes operational.
- [ ] [L380] APIs operational.
- [ ] [L381] Tests passing.
- [ ] [L382] Tests failing.
- [ ] [L383] Docker health.
- [ ] [L384] Current blockers.
- [ ] [L385] First unchecked task.
- [ ] [L386] Exact next command.
- [ ] [L388] Do not mark a checkbox complete based on file existence.
- [ ] [L390] A requirement is complete only after:
- [ ] [L392] The implementation exists.
- [ ] [L393] It is integrated.
- [ ] [L394] It runs.
- [ ] [L395] Tests pass.
- [ ] [L396] Verification evidence is recorded.

### 6. MILESTONE 1 - PORTFOLIO LEDGER AND NAV ENGINE

- [ ] [L402] This is the highest-priority implementation.
- [ ] [L404] Create or complete a production-style ledger-based portfolio system.

### 6.1 Portfolio domain model

- [ ] [L408] Implement:
- [ ] [L410] Portfolio PortfolioAccount PortfolioTransaction PortfolioCashBalance PortfolioPosition PositionLot PositionValuation PortfolioValuationRun NavSnapshot DailyReturn BenchmarkReturn CapitalFlow PortfolioIncome PortfolioFee PortfolioLiability PortfolioAccrual
- [ ] [L427] Transaction types:
- [ ] [L429] DEPOSIT
- [ ] [L430] WITHDRAWAL
- [ ] [L431] BUY
- [ ] [L432] SELL
- [ ] [L433] SHORT
- [ ] [L434] COVER
- [ ] [L435] DIVIDEND
- [ ] [L436] INTEREST
- [ ] [L437] COMMISSION
- [ ] [L438] FEE
- [ ] [L439] TAX
- [ ] [L440] FX_CONVERSION
- [ ] [L441] SPLIT
- [ ] [L442] REVERSE_SPLIT
- [ ] [L443] SPINOFF
- [ ] [L444] MERGER
- [ ] [L445] TRANSFER_IN
- [ ] [L446] TRANSFER_OUT
- [ ] [L447] OTHER_ADJUSTMENT
- [ ] [L449] Each transaction must contain:
- [ ] [L451] Immutable transaction ID.
- [ ] [L452] Portfolio ID.
- [ ] [L453] Account ID.
- [ ] [L454] Instrument ID where applicable.
- [ ] [L455] Transaction type.
- [x] [L456] Trade timestamp. (Validated optional provenance; legacy unknowns explicit, not intraday order.)
- [ ] [L457] Trade date.
- [ ] [L458] Settlement date.
- [ ] [L459] Quantity.
- [ ] [L460] Price.
- [ ] [L461] Currency.
- [ ] [L462] Gross amount.
- [x] [L463] Net amount. (Replay-derived source-currency economic cash, with separate FX legs.)
- [ ] [L464] Commission.
- [ ] [L465] Fee.
- [ ] [L466] Tax.
- [ ] [L467] FX rate to SGD.
- [ ] [L468] Base-currency value.
- [ ] [L469] Source.
- [x] [L470] External reference. (Original reference separate from deduplication hash.)
- [ ] [L471] Source file ID.
- [x] [L472] Broker execution ID. (Reference only; no broker confirmation or execution.)
- [x] [L473] Strategy ID.
- [x] [L474] Thesis ID.
- [ ] [L475] Notes.
- [ ] [L476] Reconciliation status.
- [ ] [L477] Created timestamp.
- [ ] [L478] Updated timestamp.
- [x] [L479] Created by. (Actual creation audit actor; anonymous/legacy unknowns explicit.)
- [ ] [L480] Audit version.
- [ ] [L482] Positions must be derived from transactions.
- [ ] [L484] Do not treat a directly editable position quantity as the source of truth.

### 6.2 Cost-basis engine

- [ ] [L489] Implement and test:
- [x] [L491] Weighted-average cost.
- [x] [L492] FIFO cost basis.
- [x] [L493] Configurable cost-basis method.
- [x] [L494] Partial sale.
- [x] [L495] Full sale.
- [x] [L496] Short positions.
- [x] [L497] Partial short cover.
- [x] [L498] Currency conversion.
- [x] [L499] Commissions included in cost basis.
- [x] [L500] Fees included where configured.
- [x] [L501] Corporate actions.
- [x] [L502] Fractional quantities.
- [ ] [L503] Rounding rules.

### 6.3 Cash engine

- [ ] [L507] Track cash by currency.
- [ ] [L509] Support:
- [ ] [L511] SGD.
- [ ] [L512] USD.
- [ ] [L513] Other configured currencies.
- [ ] [L514] Deposits.
- [ ] [L515] Withdrawals.
- [ ] [L516] Trade settlement.
- [ ] [L517] Commissions.
- [ ] [L518] Fees.
- [ ] [L519] Dividends.
- [ ] [L520] Interest.
- [ ] [L521] Taxes.
- [ ] [L522] FX conversion.
- [ ] [L523] Pending settlement.
- [ ] [L524] Available cash.
- [ ] [L525] Total cash in SGD.

### 6.4 Position engine

- [ ] [L529] Calculate:
- [x] [L531] Quantity.
- [x] [L532] Long or short direction.
- [x] [L533] Average cost.
- [x] [L534] Cost basis.
- [x] [L535] Current price. (Selected mark with timestamp/state, not an assertion of live data.)
- [x] [L536] Market value. (Native currency, signed quantity and contract multiplier.)
- [x] [L537] SGD market value. (Configured base currency; missing FX explicitly unavailable.)
- [x] [L538] Realised P&L.
- [x] [L539] Unrealised P&L. (Separate native/base and price/FX components.)
- [x] [L540] Total P&L.
- [x] [L541] Daily P&L. (Recorded cash/marks; explicit corporate reference allocation; missing marks unavailable.)
- [x] [L542] Portfolio weight. (Signed marked value / NAV; unknown and zero NAV distinct.)
- [x] [L543] Sector weight.
- [ ] [L544] Currency exposure.
- [ ] [L545] Country exposure.
- [ ] [L546] Asset-class exposure.
- [x] [L547] Beta contribution. (Weight times available beta; insufficient beta remains null.)
- [ ] [L548] Risk contribution.
- [ ] [L549] Data freshness.
- [ ] [L550] Price source.
- [ ] [L551] FX source.

### 6.5 NAV calculation

- [ ] [L555] Implement:
- [ ] [L557] Gross Asset Value = Cash + Position Market Values + Accrued Income + Receivables
- [ ] [L563] NAV = Gross Asset Value
- [ ] [L565] Liabilities
- [ ] [L566] Accrued Fees
- [ ] [L567] Payables
- [ ] [L569] For every position:
- [ ] [L571] Market Value in SGD = Quantity x Price x Contract Multiplier x FX-to-SGD Rate
- [ ] [L577] Store:
- [ ] [L579] Opening NAV.
- [ ] [L580] Closing NAV.
- [ ] [L581] Latest NAV.
- [ ] [L582] Gross asset value.
- [ ] [L583] Cash.
- [ ] [L584] Invested value.
- [ ] [L585] Accrued income.
- [ ] [L586] Liabilities.
- [ ] [L587] Fees.
- [ ] [L588] External capital flows.
- [ ] [L589] Daily P&L.
- [ ] [L590] Daily return.
- [ ] [L591] Price timestamp.
- [ ] [L592] FX timestamp.
- [ ] [L593] Calculation timestamp.
- [ ] [L594] Price-source state.
- [ ] [L595] Data-quality state.
- [ ] [L596] Percentage of NAV using stale data.

### 6.6 Portfolio views

- [ ] [L600] Implement two strictly separated views.
- [ ] [L602] BROKER ACCOUNT VIEW:
- [ ] [L604] Uses broker-reported data.
- [ ] [L605] Displays broker-reported NAV.
- [ ] [L606] Displays broker cash.
- [ ] [L607] Displays broker positions.
- [ ] [L608] Displays broker P&L.
- [ ] [L609] Shows PAPER badge.
- [ ] [L611] KNK REFERENCE PORTFOLIO VIEW:
- [ ] [L613] Starts from SGD 70,000.
- [ ] [L614] Uses internal ledger.
- [ ] [L615] Calculates internal NAV.
- [ ] [L616] Calculates internal performance.
- [ ] [L617] Displays CALCULATED badge.
- [ ] [L618] Shows price-source state.
- [ ] [L620] Never silently mix them.

### 6.7 Default portfolio

- [ ] [L624] Seed:
- [ ] [L626] Portfolio code:
- [ ] [L627] KNK_MAIN
- [ ] [L629] Opening contribution: SGD 70,000 exactly
- [ ] [L632] The current NAV must be reconstructed using:
- [ ] [L634] Opening contribution.
- [ ] [L635] Transactions.
- [ ] [L636] Prices.
- [ ] [L637] FX.
- [ ] [L638] Fees.
- [ ] [L639] Dividends.
- [ ] [L640] Current valuation.
- [ ] [L642] Do not hardcode NAV or return in the frontend.
- [ ] [L644] Provide:
- [ ] [L646] Reset Demo Portfolio
- [ ] [L648] The reset action must recreate identical deterministic data.

### 6.8 Portfolio services

- [ ] [L652] Implement:
- [ ] [L654] PortfolioLedgerService PortfolioTransactionService CostBasisService PortfolioCashService PortfolioPositionService PortfolioValuationService NavCalculationService PortfolioPerformanceService PortfolioAttributionService PortfolioRecalculationService

### 6.9 Portfolio APIs

- [ ] [L667] Implement:
- [ ] [L669] GET    /api/v1/portfolios
- [ ] [L670] POST   /api/v1/portfolios
- [ ] [L671] GET    /api/v1/portfolios/{portfolio_id}
- [ ] [L672] GET    /api/v1/portfolios/{portfolio_id}/summary
- [ ] [L673] GET    /api/v1/portfolios/{portfolio_id}/positions
- [ ] [L674] GET    /api/v1/portfolios/{portfolio_id}/positions/{position_id}
- [ ] [L675] GET    /api/v1/portfolios/{portfolio_id}/transactions
- [ ] [L676] POST   /api/v1/portfolios/{portfolio_id}/transactions
- [ ] [L677] GET    /api/v1/portfolios/{portfolio_id}/transactions/{transaction_id}
- [ ] [L678] PUT    /api/v1/portfolios/{portfolio_id}/transactions/{transaction_id}
- [ ] [L679] DELETE /api/v1/portfolios/{portfolio_id}/transactions/{transaction_id}
- [ ] [L680] GET    /api/v1/portfolios/{portfolio_id}/cash
- [ ] [L681] GET    /api/v1/portfolios/{portfolio_id}/nav
- [ ] [L682] POST   /api/v1/portfolios/{portfolio_id}/value
- [ ] [L683] POST   /api/v1/portfolios/{portfolio_id}/recalculate
- [ ] [L684] GET    /api/v1/portfolios/{portfolio_id}/performance
- [ ] [L685] GET    /api/v1/portfolios/{portfolio_id}/attribution
- [ ] [L686] POST   /api/v1/portfolios/{portfolio_id}/reset-demo
- [ ] [L688] All mutations must create audit events.

### 7. MILESTONE 2 - PERFORMANCE AND ATTRIBUTION

- [ ] [L694] Implement actual calculations.

### 7.1 Performance calculations

- [ ] [L698] Implement:
- [ ] [L700] Daily P&L.
- [ ] [L701] Daily return.
- [ ] [L702] Time-weighted return.
- [ ] [L703] Chain-linked return.
- [ ] [L704] Money-weighted return.
- [ ] [L705] XIRR.
- [ ] [L706] MTD.
- [ ] [L707] QTD.
- [ ] [L708] YTD.
- [ ] [L709] One-year return.
- [ ] [L710] Since-inception return.
- [ ] [L711] CAGR.
- [ ] [L712] Annualised volatility.
- [ ] [L713] Sharpe ratio.
- [ ] [L714] Sortino ratio.
- [ ] [L715] Calmar ratio.
- [ ] [L716] Maximum drawdown.
- [ ] [L717] Current drawdown.
- [ ] [L718] Drawdown duration.
- [ ] [L719] Recovery duration.
- [ ] [L720] Beta.
- [ ] [L721] Alpha.
- [ ] [L722] Tracking error.
- [ ] [L723] Information ratio.
- [ ] [L724] Upside capture.
- [ ] [L725] Downside capture.
- [ ] [L726] Daily win rate.
- [ ] [L727] Monthly win rate.
- [ ] [L728] Best day.
- [ ] [L729] Worst day.
- [ ] [L730] Best month.
- [ ] [L731] Worst month.
- [ ] [L733] Use configurable:
- [ ] [L735] Risk-free rate.
- [ ] [L736] Trading days.
- [ ] [L737] Benchmark.
- [ ] [L738] Date range.
- [ ] [L739] Return frequency.
- [ ] [L740] Gross/net of fees.
- [ ] [L742] Return a structured insufficient-data result when the requested metric cannot be calculated reliably.
- [ ] [L745] Do not return misleading zeroes.

### 7.2 Attribution

- [ ] [L749] Implement contribution by:
- [ ] [L751] Security.
- [ ] [L752] Sector.
- [ ] [L753] Industry.
- [ ] [L754] Country.
- [ ] [L755] Currency.
- [ ] [L756] Asset class.
- [ ] [L757] Strategy.
- [ ] [L758] Factor.
- [ ] [L759] Hedge.
- [ ] [L760] Dividend.
- [ ] [L761] Commission.
- [ ] [L762] Fee.
- [ ] [L763] FX.
- [ ] [L764] Allocation.
- [ ] [L765] Selection where methodology supports it.
- [ ] [L767] Store attribution runs and results.

### 7.3 Performance APIs

- [ ] [L771] Implement:
- [ ] [L773] GET  /api/v1/performance/portfolios/{portfolio_id}/summary
- [ ] [L774] GET  /api/v1/performance/portfolios/{portfolio_id}/series
- [ ] [L775] GET  /api/v1/performance/portfolios/{portfolio_id}/drawdowns
- [ ] [L776] GET  /api/v1/performance/portfolios/{portfolio_id}/monthly
- [ ] [L777] GET  /api/v1/performance/portfolios/{portfolio_id}/rolling
- [ ] [L778] GET  /api/v1/attribution/portfolios/{portfolio_id}
- [ ] [L779] POST /api/v1/performance/portfolios/{portfolio_id}/calculate

### 8. MILESTONE 3 - PRICE, FX, SOURCE PRECEDENCE, AND FRESHNESS

- [ ] [L785] Implement a formal source-management architecture.

### 8.1 Market price resolver

- [ ] [L789] Implement:
- [ ] [L791] MarketPriceResolver
- [ ] [L793] Source order must be configurable.
- [ ] [L795] Default order:
- [ ] [L797] 1. IBKR paper quote when connected and entitled.
- [ ] [L798] 2. Connected market-data API.
- [ ] [L799] 3. Latest validated imported file.
- [ ] [L800] 4. Demo provider.
- [ ] [L802] Every resolved price must contain:
- [ ] [L804] Instrument.
- [ ] [L805] Price.
- [ ] [L806] Currency.
- [ ] [L807] Source.
- [ ] [L808] Provider.
- [ ] [L809] Dataset version.
- [ ] [L810] Source file.
- [ ] [L811] Market timestamp.
- [ ] [L812] Ingestion timestamp.
- [ ] [L813] Selected source priority.
- [ ] [L814] Adjustment state.
- [ ] [L815] Freshness state.
- [ ] [L816] Data-quality state.
- [ ] [L818] Price states:
- [ ] [L820] LIVE
- [ ] [L821] DELAYED
- [ ] [L822] EOD
- [ ] [L823] FILE_IMPORT
- [ ] [L824] DEMO
- [ ] [L825] STALE
- [ ] [L826] UNAVAILABLE
- [ ] [L828] Do not label imported Koyfin data as live.

### 8.2 FX resolver

- [ ] [L832] Implement:
- [ ] [L834] FxRateResolver
- [ ] [L836] Source order:
- [ ] [L838] 1. Connected FX provider.
- [ ] [L839] 2. IBKR paper FX quote.
- [ ] [L840] 3. Validated imported FX file.
- [ ] [L841] 4. Demo provider.
- [ ] [L843] Support:
- [ ] [L845] Direct pairs.
- [ ] [L846] Inverse pairs.
- [ ] [L847] Cross-rate calculation.
- [ ] [L848] Timestamp matching.
- [ ] [L849] Missing FX warnings.
- [ ] [L850] Stale FX warnings.
- [ ] [L851] Base-currency conversion.
- [ ] [L852] Source provenance.

### 8.3 Source conflict management

- [ ] [L856] Store every competing source value.
- [ ] [L858] Implement:
- [ ] [L860] DataSourcePrecedenceService SourceConflictService SourceOverrideService
- [ ] [L864] When different sources materially disagree:
- [ ] [L866] Store both.
- [ ] [L867] Apply source-precedence rules.
- [ ] [L868] Show selected value.
- [ ] [L869] Show competing values.
- [ ] [L870] Calculate difference.
- [ ] [L871] Flag conflict.
- [ ] [L872] Allow administrator override.
- [ ] [L873] Audit the override.

### 8.4 Freshness service

- [ ] [L877] Implement:
- [ ] [L879] DataFreshnessService
- [ ] [L881] Configurable tolerances by:
- [ ] [L883] Asset class.
- [ ] [L884] Dataset type.
- [ ] [L885] Provider.
- [ ] [L886] Frequency.
- [ ] [L887] Market state.
- [ ] [L889] Display:
- [ ] [L891] Age.
- [ ] [L892] Freshness status.
- [ ] [L893] Expected refresh interval.
- [ ] [L894] Last valid value.
- [ ] [L895] Percentage of NAV affected by stale data.

### 9. MILESTONE 4 - KOYFIN AND EXTERNAL DATA DROP

- [ ] [L901] The terminal must support external files exported from Koyfin Plus and other sources.
- [ ] [L904] Koyfin is not a direct API provider.
- [ ] [L906] Do not scrape Koyfin.
- [ ] [L908] Do not reverse-engineer Koyfin.
- [ ] [L910] Implement a proper file-based bridge.

### 9.1 Supported formats

- [ ] [L914] Tabular:
- [ ] [L916] CSV.
- [ ] [L917] XLSX.
- [ ] [L918] XLS.
- [ ] [L919] Parquet.
- [ ] [L920] JSON.
- [ ] [L921] JSONL.
- [ ] [L923] Research attachments:
- [ ] [L925] PDF.
- [ ] [L926] PNG.
- [ ] [L927] JPG.
- [ ] [L928] WebP.

### 9.2 Supported dataset classes

- [ ] [L932] Daily OHLCV.
- [ ] [L933] Intraday OHLCV.
- [ ] [L934] Price history.
- [ ] [L935] Equity snapshot.
- [ ] [L936] Fundamentals.
- [ ] [L937] Financial statements.
- [ ] [L938] Valuation metrics.
- [ ] [L939] Analyst estimates.
- [ ] [L940] Technical indicators.
- [ ] [L941] Watchlists.
- [ ] [L942] Macro observations.
- [ ] [L943] FX history.
- [ ] [L944] Portfolio transactions.
- [ ] [L945] Portfolio positions.
- [ ] [L946] Factor values.
- [ ] [L947] Options chains.
- [ ] [L948] Alternative data.
- [ ] [L949] Model features.
- [ ] [L950] Training labels.
- [ ] [L951] Custom tables.

### 9.3 Filename parser

- [ ] [L955] Support:
- [ ] [L957] AAPL_2026-08-31_prices_daily.csv AAPL_2026-08-31_fundamentals.xlsx AAPL_2026-08-31.csv AAPL 2026-08-31.csv AAPL-2026-08-31.csv PORTFOLIO_2026-08-31_transactions.csv USDSGD_2026-08-31_fx.csv
- [ ] [L965] Attempt to detect:
- [ ] [L967] Symbol.
- [ ] [L968] As-of date.
- [ ] [L969] Dataset type.
- [ ] [L970] Frequency.
- [ ] [L971] Source.
- [ ] [L973] Never trust filename metadata without validating file contents.

### 9.4 File ingestion state machine

- [ ] [L977] Implement:
- [ ] [L979] DETECTED
- [ ] [L980] HASHING
- [ ] [L981] UPLOADING
- [ ] [L982] STORED_RAW
- [ ] [L983] PREVIEWING
- [ ] [L984] SCHEMA_DETECTED
- [ ] [L985] MAPPING_REQUIRED
- [ ] [L986] MAPPED
- [ ] [L987] VALIDATING
- [ ] [L988] VALIDATED_WITH_WARNINGS
- [ ] [L989] VALIDATED
- [ ] [L990] AWAITING_APPROVAL
- [ ] [L991] IMPORTING
- [ ] [L992] IMPORTED
- [ ] [L993] ARCHIVED
- [ ] [L995] Failure states:
- [ ] [L997] DUPLICATE
- [ ] [L998] REJECTED
- [ ] [L999] QUARANTINED
- [ ] [L1000] UPLOAD_FAILED
- [ ] [L1001] VALIDATION_FAILED
- [ ] [L1002] IMPORT_FAILED

### 9.5 File record

- [ ] [L1006] Store:
- [ ] [L1008] File ID.
- [ ] [L1009] SHA-256 hash.
- [ ] [L1010] Original filename.
- [ ] [L1011] Original local path reference.
- [ ] [L1012] Size.
- [ ] [L1013] MIME type.
- [ ] [L1014] Source.
- [ ] [L1015] Symbol.
- [ ] [L1016] Dataset type.
- [ ] [L1017] As-of date.
- [ ] [L1018] Detected time.
- [ ] [L1019] Uploaded time.
- [ ] [L1020] Validation result.
- [ ] [L1021] Mapping profile.
- [ ] [L1022] Dataset ID.
- [ ] [L1023] Dataset version.
- [ ] [L1024] Raw-object location.
- [ ] [L1025] Curated-object location.
- [ ] [L1026] Import status.
- [ ] [L1027] Archive status.
- [ ] [L1028] Error details.

### 9.6 Mapping profiles

- [ ] [L1032] Implement versioned mapping profiles:
- [ ] [L1034] KOYFIN_PRICE_HISTORY
- [ ] [L1035] KOYFIN_EQUITY_SNAPSHOT
- [ ] [L1036] KOYFIN_WATCHLIST_EXPORT
- [ ] [L1037] KOYFIN_TECHNICAL_EXPORT
- [ ] [L1038] KOYFIN_FUND_EXPORT
- [ ] [L1039] KOYFIN_MACRO_EXPORT
- [ ] [L1040] GENERIC_OHLCV
- [ ] [L1041] GENERIC_FUNDAMENTALS_LONG
- [ ] [L1042] GENERIC_FUNDAMENTALS_WIDE
- [ ] [L1043] GENERIC_PORTFOLIO_TRANSACTIONS
- [ ] [L1044] GENERIC_POSITIONS
- [ ] [L1045] GENERIC_FX_HISTORY
- [ ] [L1046] GENERIC_OPTIONS_CHAIN
- [ ] [L1048] Each profile must include:
- [ ] [L1050] Profile ID.
- [ ] [L1051] Version.
- [ ] [L1052] Source.
- [ ] [L1053] Dataset type.
- [ ] [L1054] Recognised aliases.
- [ ] [L1055] Required fields.
- [ ] [L1056] Optional fields.
- [ ] [L1057] Field mappings.
- [ ] [L1058] Date formats.
- [ ] [L1059] Numeric formats.
- [ ] [L1060] Currency rules.
- [ ] [L1061] Frequency.
- [ ] [L1062] Duplicate key.
- [ ] [L1063] Validation rules.
- [ ] [L1064] Transformation rules.
- [ ] [L1065] Approval state.

### 9.7 Data validation

- [ ] [L1069] Implement checks for:
- [ ] [L1071] Missing required columns.
- [ ] [L1072] Duplicate rows.
- [ ] [L1073] Duplicate dates.
- [ ] [L1074] Invalid dates.
- [ ] [L1075] Invalid timestamps.
- [ ] [L1076] Invalid numeric values.
- [ ] [L1077] Negative volumes.
- [ ] [L1078] Invalid OHLC relationships.
- [ ] [L1079] Unknown currencies.
- [ ] [L1080] Unknown instruments.
- [ ] [L1081] Filename/content mismatch.
- [ ] [L1082] Unexpected frequency.
- [ ] [L1083] Non-monotonic dates.
- [ ] [L1084] Missing close values.
- [ ] [L1085] Outliers.
- [ ] [L1086] Corporate-action gaps.
- [ ] [L1087] Publication-date look-ahead.
- [ ] [L1088] Reporting-period mismatch.
- [ ] [L1089] Annual/quarterly mismatch.
- [ ] [L1090] Estimate/actual mismatch.
- [ ] [L1091] Currency mismatch.
- [ ] [L1092] Scale mismatch.
- [ ] [L1093] Formula injection.
- [ ] [L1094] ZIP bombs.
- [ ] [L1095] MIME mismatch.
- [ ] [L1096] Path traversal.

### 9.8 Immutable storage

- [ ] [L1100] Original files must be stored immutably.
- [ ] [L1102] Transformed data must be stored separately.
- [ ] [L1104] Every import creates:
- [ ] [L1106] Dataset.
- [ ] [L1107] Dataset version.
- [ ] [L1108] Schema version.
- [ ] [L1109] Lineage record.
- [ ] [L1110] Raw-object reference.
- [ ] [L1111] Curated-object reference.
- [ ] [L1112] Validation record.
- [ ] [L1113] Quality score.
- [ ] [L1115] Never silently overwrite a dataset version used by a completed backtest.

### 9.9 Data Drop APIs

- [ ] [L1119] Implement:
- [ ] [L1121] POST /api/v1/data-drop/files
- [ ] [L1122] GET  /api/v1/data-drop/files
- [ ] [L1123] GET  /api/v1/data-drop/files/{file_id}
- [ ] [L1124] POST /api/v1/data-drop/files/{file_id}/preview
- [ ] [L1125] POST /api/v1/data-drop/files/{file_id}/classify
- [ ] [L1126] POST /api/v1/data-drop/files/{file_id}/map
- [ ] [L1127] POST /api/v1/data-drop/files/{file_id}/validate
- [ ] [L1128] POST /api/v1/data-drop/files/{file_id}/import
- [ ] [L1129] POST /api/v1/data-drop/files/{file_id}/reject
- [ ] [L1130] POST /api/v1/data-drop/files/{file_id}/quarantine
- [ ] [L1131] GET  /api/v1/data-drop/mapping-profiles
- [ ] [L1132] POST /api/v1/data-drop/mapping-profiles
- [ ] [L1133] PUT  /api/v1/data-drop/mapping-profiles/{profile_id}

### 9.10 Data Catalogue APIs

- [ ] [L1137] Implement:
- [ ] [L1139] GET /api/v1/datasets
- [ ] [L1140] GET /api/v1/datasets/{dataset_id}
- [ ] [L1141] GET /api/v1/datasets/{dataset_id}/versions
- [ ] [L1142] GET /api/v1/datasets/{dataset_id}/versions/{version_id}
- [ ] [L1143] GET /api/v1/datasets/{dataset_id}/preview
- [ ] [L1144] GET /api/v1/datasets/{dataset_id}/quality
- [ ] [L1145] GET /api/v1/datasets/{dataset_id}/lineage
- [ ] [L1146] GET /api/v1/datasets/{dataset_id}/consumers
- [ ] [L1147] GET /api/v1/datasets/{dataset_id}/conflicts

### 10. MILESTONE 5 - LOCAL DATA AGENT

- [ ] [L1153] Create or extend a Windows-compatible KnK Local Agent.
- [ ] [L1155] The local agent contains:
- [ ] [L1157] 1. External file-drop watcher.
- [ ] [L1158] 2. IBKR read-only connector.
- [ ] [L1160] The modules must remain permission-separated.

### 10.1 Watched folder

- [ ] [L1164] Configuration:
- [ ] [L1166] KNK_LOCAL_AGENT_ENABLED=true KNK_DATA_DROP_ENABLED=true KNK_DATA_DROP_ROOT= KNK_DATA_DROP_SCAN_INTERVAL_SECONDS=5 KNK_DATA_DROP_AUTO_UPLOAD=true KNK_DATA_DROP_AUTO_IMPORT_KNOWN_SCHEMAS=false KNK_DATA_DROP_ARCHIVE_PROCESSED=true
- [ ] [L1174] Folder structure:
- [ ] [L1176] KnK Data Drop/ ├── inbox/ │   ├── koyfin/ │   ├── prices/ │   ├── fundamentals/ │   ├── macro/ │   ├── portfolio/ │   ├── options/ │   └── custom/ ├── processing/ ├── review/ ├── processed/ │   └── YYYY/ │       └── MM/ ├── rejected/ └── logs/

### 10.2 Agent features

- [ ] [L1195] Implement:
- [ ] [L1197] Folder configuration.
- [ ] [L1198] File-system watcher.
- [ ] [L1199] Periodic fallback scan.
- [ ] [L1200] Stable-file detection.
- [ ] [L1201] SHA-256 hash.
- [ ] [L1202] Duplicate prevention.
- [ ] [L1203] Resumable upload where practical.
- [ ] [L1204] Safe retry.
- [ ] [L1205] Pause.
- [ ] [L1206] Resume.
- [ ] [L1207] Manual rescan.
- [ ] [L1208] Agent heartbeat.
- [ ] [L1209] Agent diagnostics.
- [ ] [L1210] Secure pairing.
- [ ] [L1211] Revocation.
- [ ] [L1212] Local structured logs.
- [ ] [L1213] Secret redaction.
- [ ] [L1214] Windows Credential Manager.
- [ ] [L1215] Foreground console mode.
- [ ] [L1216] Startup mode.
- [ ] [L1217] Windows service installation scripts where practical.
- [ ] [L1218] System tray status where practical.
- [ ] [L1220] The agent must use outbound connections only.
- [ ] [L1222] No inbound public port.

### 10.3 Local-agent APIs

- [ ] [L1226] Implement:
- [ ] [L1228] POST /api/v1/local-agents/pairing-codes
- [ ] [L1229] POST /api/v1/local-agents/pair
- [ ] [L1230] GET  /api/v1/local-agents
- [ ] [L1231] GET  /api/v1/local-agents/{agent_id}
- [ ] [L1232] POST /api/v1/local-agents/{agent_id}/heartbeat
- [ ] [L1233] POST /api/v1/local-agents/{agent_id}/revoke
- [ ] [L1234] POST /api/v1/local-agents/{agent_id}/files/initiate
- [ ] [L1235] POST /api/v1/local-agents/{agent_id}/files/{file_id}/complete

### 11. MILESTONE 6 - FRED, SEC, OPENFIGI, AND PROVIDER CORE

- [ ] [L1241] Implement a real provider registry.
- [ ] [L1243] Provider states:
- [ ] [L1245] DISABLED
- [ ] [L1246] NOT_CONFIGURED
- [ ] [L1247] CONNECTING
- [ ] [L1248] CONNECTED
- [ ] [L1249] DEGRADED
- [ ] [L1250] RATE_LIMITED
- [ ] [L1251] FAILED
- [ ] [L1253] Provider interface:
- [ ] [L1255] provider_name
- [ ] [L1256] capabilities
- [ ] [L1257] test_connection
- [ ] [L1258] health_check
- [ ] [L1259] last_success
- [ ] [L1260] last_failure
- [ ] [L1261] last_error
- [ ] [L1262] data_freshness
- [ ] [L1263] rate_limit_state

### 11.1 FRED provider

- [ ] [L1267] Implement a complete FRED adapter using environment variables.
- [ ] [L1269] Capabilities:
- [ ] [L1271] Test connection.
- [ ] [L1272] Search series.
- [ ] [L1273] Retrieve metadata.
- [ ] [L1274] Retrieve observations.
- [ ] [L1275] Retrieve releases.
- [ ] [L1276] Retrieve vintage information where supported.
- [ ] [L1277] Backfill selected series.
- [ ] [L1278] Incrementally refresh.
- [ ] [L1279] Detect revisions.
- [ ] [L1280] Preserve prior versions.
- [ ] [L1281] Store raw response.
- [ ] [L1282] Store curated observations.
- [ ] [L1283] Update provider health.
- [ ] [L1284] Publish job progress.
- [ ] [L1286] Default series catalogue should include verified series representing:
- [ ] [L1288] Policy rate.
- [ ] [L1289] Effective federal funds rate.
- [ ] [L1290] SOFR.
- [ ] [L1291] 2Y Treasury.
- [ ] [L1292] 10Y Treasury.
- [ ] [L1293] 2s10s spread.
- [ ] [L1294] CPI.
- [ ] [L1295] Core CPI.
- [ ] [L1296] PCE.
- [ ] [L1297] Core PCE.
- [ ] [L1298] Unemployment.
- [ ] [L1299] Payroll employment.
- [ ] [L1300] Real GDP.
- [ ] [L1301] Industrial production.
- [ ] [L1302] Retail sales.
- [ ] [L1303] High-yield spread.
- [ ] [L1304] Dollar index.
- [ ] [L1305] Volatility index.
- [ ] [L1307] Missing observations must be missing, not zero.

### 11.2 SEC EDGAR provider

- [ ] [L1311] Implement:
- [ ] [L1313] CIK mapping.
- [ ] [L1314] Company submissions.
- [ ] [L1315] Filing metadata.
- [ ] [L1316] 10-K.
- [ ] [L1317] 10-Q.
- [ ] [L1318] 8-K.
- [ ] [L1319] 20-F.
- [ ] [L1320] 6-K.
- [ ] [L1321] XBRL company facts.
- [ ] [L1322] Accession numbers.
- [ ] [L1323] Filing timestamps.
- [ ] [L1324] Amendment status.
- [ ] [L1325] Raw filing references.
- [ ] [L1326] Rate control.
- [ ] [L1327] Declared user agent.
- [ ] [L1328] Filing search.
- [ ] [L1329] Incremental refresh.

### 11.3 OpenFIGI provider

- [ ] [L1333] Implement:
- [ ] [L1335] Symbol mapping.
- [ ] [L1336] FIGI.
- [ ] [L1337] Composite FIGI.
- [ ] [L1338] Share-class FIGI.
- [ ] [L1339] ISIN.
- [ ] [L1340] Exchange.
- [ ] [L1341] Security type.
- [ ] [L1342] Vendor mapping.
- [ ] [L1343] Rate-limit handling.
- [ ] [L1344] Batch mapping.
- [ ] [L1345] Mapping conflict handling.

### 11.4 Optional provider adapters

- [ ] [L1349] Create production-ready adapter boundaries for:
- [ ] [L1351] EODHD.
- [ ] [L1352] FMP.
- [ ] [L1353] Polygon.
- [ ] [L1354] Databento.
- [ ] [L1355] News provider.
- [ ] [L1356] Options provider.
- [ ] [L1357] Crypto provider.
- [ ] [L1359] When credentials are missing:
- [ ] [L1361] Provider remains NOT_CONFIGURED.
- [ ] [L1362] Demo data remain available.
- [ ] [L1363] No fake connected state.
- [ ] [L1364] No application failure.

### 12. MILESTONE 7 - TRADE MONITOR AND RECONCILIATION

- [ ] [L1370] Create:
- [ ] [L1372] /trade-monitor
- [ ] [L1374] Register:
- [ ] [L1376] TRADE MONITOR
- [ ] [L1377] TRADES
- [ ] [L1378] RECON

### 12.1 Trade events

- [ ] [L1382] Sources:
- [ ] [L1384] Manual transaction.
- [ ] [L1385] IBKR paper fill.
- [ ] [L1386] Imported broker statement.
- [ ] [L1387] Imported transaction file.
- [ ] [L1388] Portfolio adjustment.
- [ ] [L1390] Store:
- [ ] [L1392] Trade event ID.
- [ ] [L1393] Source.
- [ ] [L1394] Portfolio.
- [ ] [L1395] Account.
- [ ] [L1396] Instrument.
- [ ] [L1397] Side.
- [ ] [L1398] Quantity.
- [ ] [L1399] Price.
- [ ] [L1400] Currency.
- [ ] [L1401] Gross value.
- [ ] [L1402] Commission.
- [ ] [L1403] Fee.
- [ ] [L1404] Trade timestamp.
- [ ] [L1405] Detection timestamp.
- [ ] [L1406] Broker reference.
- [ ] [L1407] Internal transaction reference.
- [ ] [L1408] Thesis.
- [ ] [L1409] Strategy.
- [ ] [L1410] Review status.
- [ ] [L1411] Reconciliation status.

### 12.2 Pre/post trade risk

- [ ] [L1415] Calculate:
- [ ] [L1417] Portfolio weight before.
- [ ] [L1418] Portfolio weight after.
- [ ] [L1419] Cash before.
- [ ] [L1420] Cash after.
- [ ] [L1421] Gross exposure before.
- [ ] [L1422] Gross exposure after.
- [ ] [L1423] Net exposure before.
- [ ] [L1424] Net exposure after.
- [ ] [L1425] Beta before.
- [ ] [L1426] Beta after.
- [ ] [L1427] Sector exposure before.
- [ ] [L1428] Sector exposure after.
- [ ] [L1429] Currency exposure before.
- [ ] [L1430] Currency exposure after.
- [ ] [L1431] Risk-limit effects.
- [ ] [L1432] VaR estimate before.
- [ ] [L1433] VaR estimate after.

### 12.3 Reconciliation

- [ ] [L1437] Compare:
- [ ] [L1439] Internal transactions versus broker fills.
- [ ] [L1440] Internal positions versus broker positions.
- [ ] [L1441] Internal cash versus broker cash.
- [ ] [L1442] Internal commissions versus broker commissions.
- [ ] [L1443] Internal NAV versus broker NAV.
- [ ] [L1444] Imported statement versus internal ledger.
- [ ] [L1445] Imported trade file versus internal ledger.
- [ ] [L1447] Break types:
- [ ] [L1449] MISSING_TRANSACTION
- [ ] [L1450] DUPLICATE_TRANSACTION
- [ ] [L1451] QUANTITY_MISMATCH
- [ ] [L1452] PRICE_MISMATCH
- [ ] [L1453] COST_BASIS_MISMATCH
- [ ] [L1454] COMMISSION_MISMATCH
- [ ] [L1455] CURRENCY_MISMATCH
- [ ] [L1456] UNKNOWN_INSTRUMENT
- [ ] [L1457] MISSING_FX
- [ ] [L1458] MISSING_PRICE
- [ ] [L1459] STALE_PRICE
- [ ] [L1460] NAV_MISMATCH
- [ ] [L1461] BROKER_SNAPSHOT_STALE
- [ ] [L1463] Each break must contain:
- [ ] [L1465] Severity.
- [ ] [L1466] Internal value.
- [ ] [L1467] External value.
- [ ] [L1468] Difference.
- [ ] [L1469] Source.
- [ ] [L1470] Detected time.
- [ ] [L1471] Assigned user.
- [ ] [L1472] Status.
- [ ] [L1473] Resolution note.
- [ ] [L1474] Audit history.

### 13. MILESTONE 8 - RISK ENGINE

- [ ] [L1480] Implement complete portfolio-risk services.

### 13.1 Exposure

- [ ] [L1484] Calculate:
- [ ] [L1486] Long exposure.
- [ ] [L1487] Short exposure.
- [ ] [L1488] Gross exposure.
- [ ] [L1489] Net exposure.
- [ ] [L1490] Cash percentage.
- [ ] [L1491] Leverage.
- [ ] [L1492] Single-name concentration.
- [ ] [L1493] Top-five concentration.
- [ ] [L1494] Herfindahl concentration.
- [ ] [L1495] Sector exposure.
- [ ] [L1496] Industry exposure.
- [ ] [L1497] Country exposure.
- [ ] [L1498] Currency exposure.
- [ ] [L1499] Exchange exposure.
- [ ] [L1500] Asset-class exposure.
- [ ] [L1501] Strategy exposure.
- [ ] [L1502] Factor exposure.

### 13.2 Statistical risk

- [ ] [L1506] Implement:
- [ ] [L1508] Historical volatility.
- [ ] [L1509] Annualised volatility.
- [ ] [L1510] EWMA volatility.
- [ ] [L1511] Covariance matrix.
- [ ] [L1512] Correlation matrix.
- [ ] [L1513] Portfolio beta.
- [ ] [L1514] Rolling beta.
- [ ] [L1515] Position beta contribution.
- [ ] [L1516] Marginal risk contribution.
- [ ] [L1517] Component risk contribution.
- [ ] [L1518] Percentage risk contribution.
- [ ] [L1519] Downside deviation.
- [ ] [L1520] Tracking error.

### 13.3 VaR and CVaR

- [ ] [L1524] Implement:
- [ ] [L1526] Historical VaR Parametric VaR Monte Carlo VaR Historical CVaR Parametric expected shortfall where appropriate
- [ ] [L1532] Parameters:
- [ ] [L1534] 95%.
- [ ] [L1535] 99%.
- [ ] [L1536] 1 day.
- [ ] [L1537] 10 days.
- [ ] [L1538] Configurable lookback.
- [ ] [L1539] Configurable covariance method.
- [ ] [L1540] Configurable simulation count.
- [ ] [L1541] Deterministic simulation seed.

### 13.4 Risk limits

- [ ] [L1545] Support:
- [ ] [L1547] Maximum single position.
- [ ] [L1548] Maximum top-five concentration.
- [ ] [L1549] Maximum sector.
- [ ] [L1550] Maximum industry.
- [ ] [L1551] Maximum country.
- [ ] [L1552] Maximum currency.
- [ ] [L1553] Maximum gross.
- [ ] [L1554] Maximum net.
- [ ] [L1555] Maximum beta.
- [ ] [L1556] Maximum volatility.
- [ ] [L1557] Maximum VaR.
- [ ] [L1558] Maximum CVaR.
- [ ] [L1559] Maximum drawdown.
- [ ] [L1560] Minimum cash.
- [ ] [L1561] Maximum leverage.
- [ ] [L1562] Maximum stale-data exposure.
- [ ] [L1564] Every breach must be persisted and audited.

### 14. MILESTONE 9 - STRESS AND HEDGE ENGINE


### 14.1 Stress testing

- [ ] [L1572] Seed:
- [ ] [L1574] SPX -5%.
- [ ] [L1575] SPX -10%.
- [ ] [L1576] NASDAQ -15%.
- [ ] [L1577] Technology -15%.
- [ ] [L1578] Financials -10%.
- [ ] [L1579] USD/SGD +5%.
- [ ] [L1580] USD/SGD -5%.
- [ ] [L1581] Rates +100bp.
- [ ] [L1582] Rates -100bp.
- [ ] [L1583] VIX +50%.
- [ ] [L1584] Oil -20%.
- [ ] [L1585] Correlation convergence.
- [ ] [L1586] 2008 crisis proxy.
- [ ] [L1587] COVID crash proxy.
- [ ] [L1588] 2022 rate-shock proxy.
- [ ] [L1589] Combined risk-off.
- [ ] [L1591] Support custom scenarios.
- [ ] [L1593] Calculate:
- [ ] [L1595] Pre-stress NAV.
- [ ] [L1596] Position P&L.
- [ ] [L1597] Sector P&L.
- [ ] [L1598] Country P&L.
- [ ] [L1599] Currency P&L.
- [ ] [L1600] Factor P&L.
- [ ] [L1601] Hedge contribution.
- [ ] [L1602] Total estimated P&L.
- [ ] [L1603] NAV impact.
- [ ] [L1604] Post-stress NAV.
- [ ] [L1605] Beta after shock.
- [ ] [L1606] Largest loss contributors.
- [ ] [L1607] Assumptions.
- [ ] [L1608] Model version.
- [ ] [L1609] Data timestamp.

### 14.2 Hedge recommendations

- [ ] [L1613] Support:
- [ ] [L1615] Broad-market ETF beta hedge.
- [ ] [L1616] Technology ETF hedge.
- [ ] [L1617] Small-cap ETF hedge.
- [ ] [L1618] Currency hedge.
- [ ] [L1619] Index micro-futures estimate.
- [ ] [L1620] Target-beta hedge.
- [ ] [L1621] Target-net-exposure hedge.
- [ ] [L1622] Sector-overweight hedge.
- [ ] [L1624] Use:
- [ ] [L1626] Required Hedge Notional = (Current Portfolio Beta - Target Beta) x Portfolio NAV ÷ Hedge Instrument Beta
- [ ] [L1631] ETF Units = Required Hedge Notional ÷ Instrument Price
- [ ] [L1635] Futures Contracts = Required Hedge Notional ÷ (Futures Price x Contract Multiplier)
- [ ] [L1639] Display:
- [ ] [L1641] Current beta.
- [ ] [L1642] Target beta.
- [ ] [L1643] Raw notional.
- [ ] [L1644] Direction.
- [ ] [L1645] Instrument.
- [ ] [L1646] Rounded quantity.
- [ ] [L1647] Residual notional.
- [ ] [L1648] Beta before and after.
- [ ] [L1649] Gross exposure before and after.
- [ ] [L1650] Net exposure before and after.
- [ ] [L1651] Estimated fees.
- [ ] [L1652] Estimated slippage.
- [ ] [L1653] Estimated VaR impact.
- [ ] [L1654] Data state.
- [ ] [L1655] Assumptions.
- [ ] [L1657] Every recommendation must say:
- [ ] [L1659] MANUAL REVIEW REQUIRED - NO ORDER WILL BE SUBMITTED

### 15. MILESTONE 10 - BACKTEST ENGINE

- [ ] [L1665] Implement a genuine native backtesting engine.

### 15.1 Backtest architecture

- [ ] [L1669] Dataset -> Universe -> Feature Calculation -> Signal -> Portfolio Construction -> Rebalance -> Fill Model -> Fees -> Slippage -> Position Accounting -> Cash Accounting -> NAV -> Performance -> Risk -> Persisted Results

### 15.2 Supported capabilities

- [ ] [L1687] Daily data.
- [ ] [L1688] Weekly data.
- [ ] [L1689] Intraday architecture where data exist.
- [ ] [L1690] Long-only.
- [ ] [L1691] Long-short.
- [ ] [L1692] Multi-security.
- [ ] [L1693] Multi-currency.
- [ ] [L1694] Initial capital.
- [ ] [L1695] Position limits.
- [ ] [L1696] Sector limits.
- [ ] [L1697] Cash minimum.
- [ ] [L1698] Equal weight.
- [ ] [L1699] Signal weight.
- [ ] [L1700] Inverse volatility.
- [ ] [L1701] Risk parity.
- [ ] [L1702] Configurable rebalance.
- [ ] [L1703] Transaction fees.
- [ ] [L1704] Spread.
- [ ] [L1705] Slippage.
- [ ] [L1706] Dividends.
- [ ] [L1707] Splits.
- [ ] [L1708] Delisting warnings.
- [ ] [L1709] Next-bar execution.
- [ ] [L1710] No look-ahead access.
- [ ] [L1711] Missing-price handling.
- [ ] [L1712] Turnover.
- [ ] [L1713] Benchmark.
- [ ] [L1714] Run cancellation.
- [ ] [L1715] Progress reporting.
- [ ] [L1716] Deterministic runs.

### 15.3 Example strategies

- [ ] [L1720] Implement working examples:
- [ ] [L1722] 1. Moving-average crossover.
- [ ] [L1723] 2. Time-series momentum.
- [ ] [L1724] 3. Cross-sectional momentum.
- [ ] [L1725] 4. Low-volatility ranking.
- [ ] [L1726] 5. Short-term mean reversion.
- [ ] [L1727] 6. Inverse-volatility portfolio.
- [ ] [L1728] 7. Risk-parity portfolio.
- [ ] [L1729] 8. Multi-factor ranking.
- [ ] [L1730] 9. Sector rotation.
- [ ] [L1731] 10. Breakout strategy.
- [ ] [L1733] Every example must display:
- [ ] [L1735] EXAMPLE RESEARCH STRATEGY - NOT AN INVESTMENT RECOMMENDATION

### 15.4 Backtest output

- [ ] [L1739] Persist:
- [ ] [L1741] Strategy.
- [ ] [L1742] Strategy version.
- [ ] [L1743] Dataset version.
- [ ] [L1744] Universe.
- [ ] [L1745] Parameters.
- [ ] [L1746] Start date.
- [ ] [L1747] End date.
- [ ] [L1748] Benchmark.
- [ ] [L1749] Initial capital.
- [ ] [L1750] Final NAV.
- [ ] [L1751] Equity curve.
- [ ] [L1752] Drawdown curve.
- [ ] [L1753] Daily returns.
- [ ] [L1754] Monthly returns.
- [ ] [L1755] Annual returns.
- [ ] [L1756] Positions.
- [ ] [L1757] Trades.
- [ ] [L1758] Exposure.
- [ ] [L1759] Turnover.
- [ ] [L1760] Fees.
- [ ] [L1761] Slippage.
- [ ] [L1762] Logs.
- [ ] [L1763] Warnings.
- [ ] [L1764] Status.
- [ ] [L1765] Worker.
- [ ] [L1766] Runtime.
- [ ] [L1768] Metrics:
- [ ] [L1770] Total return.
- [ ] [L1771] CAGR.
- [ ] [L1772] Volatility.
- [ ] [L1773] Sharpe.
- [ ] [L1774] Sortino.
- [ ] [L1775] Calmar.
- [ ] [L1776] Maximum drawdown.
- [ ] [L1777] VaR.
- [ ] [L1778] CVaR.
- [ ] [L1779] Beta.
- [ ] [L1780] Alpha.
- [ ] [L1781] Tracking error.
- [ ] [L1782] Information ratio.
- [ ] [L1783] Win rate.
- [ ] [L1784] Profit factor.
- [ ] [L1785] Average win.
- [ ] [L1786] Average loss.
- [ ] [L1787] Number of trades.

### 16. MILESTONE 11 - FACTOR, EDGE, AND MODEL LABS


### 16.1 Factor library

- [ ] [L1795] Implement:
- [ ] [L1797] 1M momentum.
- [ ] [L1798] 3M momentum.
- [ ] [L1799] 6M momentum.
- [ ] [L1800] 12M momentum.
- [ ] [L1801] Short-term reversal.
- [ ] [L1802] Volatility.
- [ ] [L1803] Beta.
- [ ] [L1804] Size.
- [ ] [L1805] Value.
- [ ] [L1806] Quality.
- [ ] [L1807] Profitability.
- [ ] [L1808] Growth.
- [ ] [L1809] Free-cash-flow yield.
- [ ] [L1810] Dividend yield.
- [ ] [L1811] Leverage.
- [ ] [L1812] Accruals.
- [ ] [L1813] Trend strength.
- [ ] [L1814] Distance from moving averages.

### 16.2 Factor diagnostics

- [ ] [L1818] Calculate:
- [ ] [L1820] Raw value.
- [ ] [L1821] Winsorised value.
- [ ] [L1822] Z-score.
- [ ] [L1823] Rank.
- [ ] [L1824] Quantile.
- [ ] [L1825] Coverage.
- [ ] [L1826] Pearson IC.
- [ ] [L1827] Spearman rank IC.
- [ ] [L1828] IC mean.
- [ ] [L1829] IC volatility.
- [ ] [L1830] IC information ratio.
- [ ] [L1831] Quantile returns.
- [ ] [L1832] Long-short spread.
- [ ] [L1833] Hit rate.
- [ ] [L1834] Signal decay.
- [ ] [L1835] Turnover.
- [ ] [L1836] Cost sensitivity.
- [ ] [L1837] Sector exposure.
- [ ] [L1838] Country exposure.
- [ ] [L1839] Factor correlation.
- [ ] [L1840] Regime stability.
- [ ] [L1841] Out-of-sample performance.

### 16.3 Edge Lab

- [ ] [L1845] Workflow:
- [ ] [L1847] Dataset -> Universe -> Hypothesis -> Factor or Signal -> Portfolio Construction -> Transaction Costs -> In-Sample Test -> Validation -> Out-of-Sample Test -> Walk-Forward -> Monte Carlo -> Paper Testing -> Approve or Reject
- [ ] [L1861] Statuses:
- [ ] [L1863] IDEA
- [ ] [L1864] RESEARCH
- [ ] [L1865] FAILED_VALIDATION
- [ ] [L1866] PAPER_TESTING
- [ ] [L1867] APPROVED_FOR_FURTHER_REVIEW
- [ ] [L1868] REJECTED
- [ ] [L1869] ARCHIVED
- [ ] [L1871] Do not label a result as a proven edge automatically.

### 16.4 Model Lab

- [ ] [L1875] Support:
- [ ] [L1877] Linear regression.
- [ ] [L1878] Logistic regression.
- [ ] [L1879] Ridge.
- [ ] [L1880] Lasso.
- [ ] [L1881] Elastic Net.
- [ ] [L1882] Decision tree.
- [ ] [L1883] Random forest.
- [ ] [L1884] Gradient boosting.
- [ ] [L1885] XGBoost adapter.
- [ ] [L1886] LightGBM adapter.
- [ ] [L1887] Ranking models.
- [ ] [L1888] Clustering.
- [ ] [L1889] Regime classification.
- [ ] [L1890] Factor composites.
- [ ] [L1891] Ensembles.
- [ ] [L1893] Require:
- [ ] [L1895] Time-aware train/validation/test split.
- [ ] [L1896] Leakage checks.
- [ ] [L1897] Feature versioning.
- [ ] [L1898] Dataset versioning.
- [ ] [L1899] Random seed.
- [ ] [L1900] Experiment tracking.
- [ ] [L1901] Feature importance.
- [ ] [L1902] Model artifact storage.
- [ ] [L1903] Out-of-sample evaluation.
- [ ] [L1904] Cost-aware backtesting.
- [ ] [L1905] Model approval status.

### 17. MILESTONE 12 - WALK-FORWARD AND MONTE CARLO


### 17.1 Walk-forward

- [ ] [L1913] Implement:
- [ ] [L1915] Rolling windows.
- [ ] [L1916] Expanding windows.
- [ ] [L1917] Training period.
- [ ] [L1918] Validation period.
- [ ] [L1919] Test period.
- [ ] [L1920] Parameter selection.
- [ ] [L1921] Refit frequency.
- [ ] [L1922] Out-of-sample aggregation.
- [ ] [L1923] Parameter stability.
- [ ] [L1924] Regime analysis.

### 17.2 Monte Carlo

- [ ] [L1928] Implement:
- [ ] [L1930] Return-path bootstrap.
- [ ] [L1931] Block bootstrap.
- [ ] [L1932] Trade-order resampling.
- [ ] [L1933] Configurable simulations.
- [ ] [L1934] Deterministic seed.
- [ ] [L1935] Median terminal value.
- [ ] [L1936] 5th percentile.
- [ ] [L1937] 95th percentile.
- [ ] [L1938] Probability of loss.
- [ ] [L1939] Maximum drawdown distribution.
- [ ] [L1940] Terminal-value distribution.
- [ ] [L1941] Confidence bands.

### 18. MILESTONE 13 - EQUITY RESEARCH ENGINE

- [ ] [L1947] Create an operational Equity Desk.

### 18.1 Security master

- [ ] [L1951] Implement:
- [ ] [L1953] Immutable internal instrument ID.
- [ ] [L1954] Symbol.
- [ ] [L1955] Name.
- [ ] [L1956] Exchange.
- [ ] [L1957] Country.
- [ ] [L1958] Currency.
- [ ] [L1959] Asset class.
- [ ] [L1960] Security type.
- [ ] [L1961] Sector.
- [ ] [L1962] Industry.
- [ ] [L1963] Listing status.
- [ ] [L1964] Provider mappings.
- [ ] [L1965] FIGI.
- [ ] [L1966] ISIN.
- [ ] [L1967] CUSIP where available.
- [ ] [L1968] IBKR contract ID where available.
- [ ] [L1969] Previous symbols.
- [ ] [L1970] Listing date.
- [ ] [L1971] Delisting date.

### 18.2 Security description

- [ ] [L1975] Implement DES:
- [ ] [L1977] Company profile.
- [ ] [L1978] Exchange.
- [ ] [L1979] Country.
- [ ] [L1980] Sector.
- [ ] [L1981] Industry.
- [ ] [L1982] Market cap.
- [ ] [L1983] Enterprise value.
- [ ] [L1984] Shares.
- [ ] [L1985] Float.
- [ ] [L1986] Currency.
- [ ] [L1987] Beta.
- [ ] [L1988] 52-week range.
- [ ] [L1989] Dividend yield.
- [ ] [L1990] Company description.
- [ ] [L1991] Identifier data.
- [ ] [L1992] Source.
- [ ] [L1993] Timestamp.

### 18.3 Financial statements

- [ ] [L1997] Implement FIN:
- [ ] [L1999] Income statement.
- [ ] [L2000] Balance sheet.
- [ ] [L2001] Cash flow.
- [ ] [L2002] Ratios.
- [ ] [L2003] Growth.
- [ ] [L2004] Margins.
- [ ] [L2005] Segments.
- [ ] [L2006] Annual.
- [ ] [L2007] Quarterly.
- [ ] [L2008] TTM.
- [ ] [L2010] Preserve:
- [ ] [L2012] Reported date.
- [ ] [L2013] Period end.
- [ ] [L2014] Currency.
- [ ] [L2015] Scale.
- [ ] [L2016] Actual/estimate.
- [ ] [L2017] Source.
- [ ] [L2018] Dataset version.

### 18.4 Valuation

- [ ] [L2022] Implement:
- [ ] [L2024] P/E.
- [ ] [L2025] Forward P/E.
- [ ] [L2026] PEG.
- [ ] [L2027] P/B.
- [ ] [L2028] P/S.
- [ ] [L2029] EV/Sales.
- [ ] [L2030] EV/EBITDA.
- [ ] [L2031] EV/EBIT.
- [ ] [L2032] FCF yield.
- [ ] [L2033] Earnings yield.
- [ ] [L2034] Dividend yield.
- [ ] [L2035] Historical median.
- [ ] [L2036] Historical percentile.
- [ ] [L2037] Peer comparison.
- [ ] [L2038] Sector comparison.
- [ ] [L2039] Premium/discount.

### 18.5 DCF

- [ ] [L2043] Implement an actual DCF engine.
- [ ] [L2045] Inputs:
- [ ] [L2047] Revenue forecast.
- [ ] [L2048] Margin forecast.
- [ ] [L2049] Tax rate.
- [ ] [L2050] D&A.
- [ ] [L2051] CapEx.
- [ ] [L2052] Working capital.
- [ ] [L2053] WACC.
- [ ] [L2054] Terminal growth.
- [ ] [L2055] Exit multiple.
- [ ] [L2056] Net debt.
- [ ] [L2057] Shares.
- [ ] [L2058] Forecast years.
- [ ] [L2059] Mid-year convention.
- [ ] [L2061] Outputs:
- [ ] [L2063] FCFF.
- [ ] [L2064] Discount factors.
- [ ] [L2065] PV of cash flows.
- [ ] [L2066] Terminal value.
- [ ] [L2067] Enterprise value.
- [ ] [L2068] Equity value.
- [ ] [L2069] Fair value per share.
- [ ] [L2070] Upside/downside.
- [ ] [L2071] Bull/base/bear.
- [ ] [L2072] Probability-weighted value.
- [ ] [L2074] Sensitivity:
- [ ] [L2076] WACC x terminal growth.
- [ ] [L2077] WACC x exit multiple.
- [ ] [L2078] Revenue growth x margin.

### 18.6 Comparables

- [ ] [L2082] Implement:
- [ ] [L2084] Peer set.
- [ ] [L2085] Market cap.
- [ ] [L2086] Enterprise value.
- [ ] [L2087] Revenue.
- [ ] [L2088] EBITDA.
- [ ] [L2089] EBIT.
- [ ] [L2090] EPS.
- [ ] [L2091] Margins.
- [ ] [L2092] Growth.
- [ ] [L2093] ROE.
- [ ] [L2094] ROIC.
- [ ] [L2095] P/E.
- [ ] [L2096] EV/EBITDA.
- [ ] [L2097] EV/Sales.
- [ ] [L2098] P/B.
- [ ] [L2099] FCF yield.
- [ ] [L2100] Median.
- [ ] [L2101] Mean.
- [ ] [L2102] Quartiles.
- [ ] [L2103] Outlier flags.
- [ ] [L2104] Implied valuation.

### 18.7 Research and thesis

- [ ] [L2108] Implement:
- [ ] [L2110] Research notes.
- [ ] [L2111] Thesis.
- [ ] [L2112] Variant perception.
- [ ] [L2113] Bull case.
- [ ] [L2114] Base case.
- [ ] [L2115] Bear case.
- [ ] [L2116] Probability weights.
- [ ] [L2117] Fair-value range.
- [ ] [L2118] Catalysts.
- [ ] [L2119] Risks.
- [ ] [L2120] Invalidation conditions.
- [ ] [L2121] Monitoring indicators.
- [ ] [L2122] Holding period.
- [ ] [L2123] Target weight.
- [ ] [L2124] Maximum weight.
- [ ] [L2125] Confidence.
- [ ] [L2126] Review date.
- [ ] [L2127] Exit thesis.
- [ ] [L2128] Post-mortem.
- [ ] [L2129] Sources.
- [ ] [L2130] Attachments.
- [ ] [L2131] Koyfin link.

### 19. MILESTONE 14 - TRADINGVIEW PINE STUDIO

- [ ] [L2137] Create:
- [ ] [L2139] /tradingview
- [ ] [L2141] Generate Pine Script for compatible strategies.
- [ ] [L2143] Support:
- [ ] [L2145] Moving-average crossover.
- [ ] [L2146] RSI threshold.
- [ ] [L2147] MACD crossover.
- [ ] [L2148] Breakout.
- [ ] [L2149] Long-only.
- [ ] [L2150] Long-short.
- [ ] [L2151] Stop loss.
- [ ] [L2152] Take profit.
- [ ] [L2153] Trailing stop.
- [ ] [L2154] Commission.
- [ ] [L2155] Slippage.
- [ ] [L2156] Date filters.
- [ ] [L2157] Session filters.
- [ ] [L2158] Alerts.
- [ ] [L2160] Create:
- [ ] [L2162] Compatibility analyser.
- [ ] [L2163] Pine generator.
- [ ] [L2164] Static validator.
- [ ] [L2165] Version history.
- [ ] [L2166] Python/Pine signal comparison.
- [ ] [L2167] Download `.pine`.
- [ ] [L2168] Copy code.
- [ ] [L2169] Manual deployment instructions.
- [ ] [L2171] Status:
- [ ] [L2173] SUPPORTED
- [ ] [L2174] PARTIALLY_SUPPORTED
- [ ] [L2175] UNSUPPORTED
- [ ] [L2177] Do not claim automatic TradingView deployment.
- [ ] [L2179] Do not send alerts to IBKR execution.
- [ ] [L2181] TradingView webhook intake may:
- [ ] [L2183] Store signal.
- [ ] [L2184] Validate signal.
- [ ] [L2185] Compare signal.
- [ ] [L2186] Alert user.
- [ ] [L2187] Create manual review.
- [ ] [L2189] It must not place an order.

### 20. MILESTONE 15 - EXCEL AND REPORT ENGINE

- [ ] [L2195] Implement a separate report-engine service or isolated worker.

### 20.1 Excel exports

- [ ] [L2199] Generate:
- [ ] [L2201] Portfolio Overview workbook.
- [ ] [L2202] Portfolio Risk workbook.
- [ ] [L2203] Backtest workbook.
- [ ] [L2204] Macro workbook.
- [ ] [L2205] Equity model.
- [ ] [L2206] DCF model.
- [ ] [L2207] Comparables workbook.
- [ ] [L2208] Factor-analysis workbook.
- [ ] [L2210] Portfolio workbook sheets:
- [ ] [L2212] Overview.
- [ ] [L2213] Holdings.
- [ ] [L2214] Transactions.
- [ ] [L2215] Cash.
- [ ] [L2216] NAV.
- [ ] [L2217] Performance.
- [ ] [L2218] Attribution.
- [ ] [L2219] Exposure.
- [ ] [L2220] Risk.
- [ ] [L2221] Stress.
- [ ] [L2222] Hedge.
- [ ] [L2223] Reconciliation.
- [ ] [L2224] Sources.
- [ ] [L2225] Checks.
- [ ] [L2227] Backtest workbook:
- [ ] [L2229] Summary.
- [ ] [L2230] Parameters.
- [ ] [L2231] Equity Curve.
- [ ] [L2232] Drawdown.
- [ ] [L2233] Monthly Returns.
- [ ] [L2234] Annual Returns.
- [ ] [L2235] Trades.
- [ ] [L2236] Positions.
- [ ] [L2237] Exposure.
- [ ] [L2238] Turnover.
- [ ] [L2239] Fees.
- [ ] [L2240] Slippage.
- [ ] [L2241] Walk-Forward.
- [ ] [L2242] Monte Carlo.
- [ ] [L2243] Sources.
- [ ] [L2244] Checks.
- [ ] [L2246] Equity model:
- [ ] [L2248] Cover.
- [ ] [L2249] Company Overview.
- [ ] [L2250] Assumptions.
- [ ] [L2251] Historical Financials.
- [ ] [L2252] Revenue Build.
- [ ] [L2253] Margin Build.
- [ ] [L2254] Forecasts.
- [ ] [L2255] DCF.
- [ ] [L2256] WACC.
- [ ] [L2257] Comparables.
- [ ] [L2258] Historical Valuation.
- [ ] [L2259] Bull/Base/Bear.
- [ ] [L2260] Sensitivity.
- [ ] [L2261] Catalysts.
- [ ] [L2262] Risks.
- [ ] [L2263] Sources.
- [ ] [L2264] Checks.
- [ ] [L2266] Formatting:
- [ ] [L2268] Inputs clearly identified.
- [ ] [L2269] Formulas distinct from inputs.
- [ ] [L2270] Source references.
- [ ] [L2271] Currency formats.
- [ ] [L2272] Percentage formats.
- [ ] [L2273] Frozen panes.
- [ ] [L2274] Print areas.
- [ ] [L2275] Sensible column widths.
- [ ] [L2276] Check rows.
- [ ] [L2277] No formula injection.
- [ ] [L2278] No screenshots pretending to be models.

### 20.2 Deck builder

- [ ] [L2282] Generate:
- [ ] [L2284] Internal IC deck.
- [ ] [L2285] Public equity-research deck.
- [ ] [L2286] Portfolio review deck.
- [ ] [L2287] Risk review deck.
- [ ] [L2288] Strategy review deck.
- [ ] [L2290] Output:
- [ ] [L2292] PPTX.
- [ ] [L2293] PDF.
- [ ] [L2294] Chart package.
- [ ] [L2295] XLSX appendix.
- [ ] [L2297] Standard equity deck:
- [ ] [L2299] 1. Cover.
- [ ] [L2300] 2. Recommendation.
- [ ] [L2301] 3. Executive Summary.
- [ ] [L2302] 4. Company Overview.
- [ ] [L2303] 5. Business Model.
- [ ] [L2304] 6. Segment Analysis.
- [ ] [L2305] 7. Industry.
- [ ] [L2306] 8. Competition.
- [ ] [L2307] 9. Investment Thesis.
- [ ] [L2308] 10. Variant Perception.
- [ ] [L2309] 11. Operating Drivers.
- [ ] [L2310] 12. Historical Financials.
- [ ] [L2311] 13. Forecasts.
- [ ] [L2312] 14. Valuation.
- [ ] [L2313] 15. DCF.
- [ ] [L2314] 16. Comparables.
- [ ] [L2315] 17. Bull/Base/Bear.
- [ ] [L2316] 18. Catalysts.
- [ ] [L2317] 19. Risks.
- [ ] [L2318] 20. Monitoring.
- [ ] [L2319] 21. Appendix.
- [ ] [L2320] 22. Sources.
- [ ] [L2321] 23. Disclosures.

### 21. MILESTONE 16 - FRONTEND PRODUCT EXPANSION

- [ ] [L2327] Preserve the approved terminal shell.
- [ ] [L2329] Implement API-driven operational pages.

### 21.1 Portfolio Command Centre

- [ ] [L2333] Route:
- [ ] [L2335] /overview
- [ ] [L2337] Replace sparse metrics with:
- [ ] [L2339] Compact portfolio KPI ribbon.
- [ ] [L2340] NAV equity curve.
- [ ] [L2341] Drawdown.
- [ ] [L2342] Positions.
- [ ] [L2343] P&L contribution.
- [ ] [L2344] Risk snapshot.
- [ ] [L2345] Trade monitor.
- [ ] [L2346] Quant monitor.
- [ ] [L2347] Research monitor.
- [ ] [L2348] Data freshness.
- [ ] [L2349] Provider health.
- [ ] [L2350] Worker health.
- [ ] [L2351] Alerts.
- [ ] [L2352] Reconciliation.
- [ ] [L2354] KPI ribbon:
- [ ] [L2356] Opening capital.
- [ ] [L2357] Current NAV.
- [ ] [L2358] Cash.
- [ ] [L2359] Invested.
- [ ] [L2360] P&L today.
- [ ] [L2361] Total P&L.
- [ ] [L2362] MTD.
- [ ] [L2363] YTD.
- [ ] [L2364] Gross.
- [ ] [L2365] Net.
- [ ] [L2366] Beta.
- [ ] [L2367] VaR.
- [ ] [L2368] Drawdown.

### 21.2 Portfolio pages

- [ ] [L2372] Implement:
- [ ] [L2374] /portfolio
- [ ] [L2375] /positions
- [ ] [L2376] /performance
- [ ] [L2377] /attribution
- [ ] [L2379] Required interactions:
- [ ] [L2381] Add transaction.
- [ ] [L2382] Edit correcting transaction.
- [ ] [L2383] Recalculate.
- [ ] [L2384] Change date.
- [ ] [L2385] Change benchmark.
- [ ] [L2386] Broker/reference toggle.
- [ ] [L2387] Export.
- [ ] [L2388] Open position.
- [ ] [L2389] Open thesis.
- [ ] [L2390] Open risk.
- [ ] [L2391] Open trade.

### 21.3 Equity dashboard

- [ ] [L2395] Route:
- [ ] [L2397] /equity
- [ ] [L2399] Show:
- [ ] [L2401] Portfolio holdings.
- [ ] [L2402] Watchlist.
- [ ] [L2403] Coverage universe.
- [ ] [L2404] Upcoming earnings.
- [ ] [L2405] Thesis reviews.
- [ ] [L2406] Fair-value upside.
- [ ] [L2407] Valuation summary.
- [ ] [L2408] Quant factors.
- [ ] [L2409] Latest Koyfin import.
- [ ] [L2410] Filing updates.
- [ ] [L2411] Research alerts.

### 21.4 Quant dashboard

- [ ] [L2415] Route:
- [ ] [L2417] /quant-dashboard
- [ ] [L2419] Show:
- [ ] [L2421] Strategies.
- [ ] [L2422] Backtest jobs.
- [ ] [L2423] Factor monitor.
- [ ] [L2424] Signals.
- [ ] [L2425] Model runs.
- [ ] [L2426] Out-of-sample results.
- [ ] [L2427] Paper-testing strategies.
- [ ] [L2428] Failed validations.
- [ ] [L2429] Dataset versions.

### 21.5 Risk and Trade dashboard

- [ ] [L2433] Route:
- [ ] [L2435] /risk-trade-monitor
- [ ] [L2437] Show:
- [ ] [L2439] NAV.
- [ ] [L2440] Day P&L.
- [ ] [L2441] Gross.
- [ ] [L2442] Net.
- [ ] [L2443] Beta.
- [ ] [L2444] Volatility.
- [ ] [L2445] VaR.
- [ ] [L2446] CVaR.
- [ ] [L2447] Drawdown.
- [ ] [L2448] Breaches.
- [ ] [L2449] Unreconciled trades.
- [ ] [L2450] Exposure panels.
- [ ] [L2451] Risk contributions.
- [ ] [L2452] Trade blotter.
- [ ] [L2453] Stress results.
- [ ] [L2454] Hedge recommendation.
- [ ] [L2455] Alert timeline.

### 21.6 Data Drop

- [ ] [L2459] Route:
- [ ] [L2461] /data-drop
- [ ] [L2463] Use split panels:
- [ ] [L2465] LEFT:
- [ ] [L2466] File inbox.
- [ ] [L2468] CENTRE:
- [ ] [L2469] Preview and column mapping.
- [ ] [L2471] RIGHT:
- [ ] [L2472] Validation and import control.

### 21.7 Data Catalogue

- [ ] [L2476] Route:
- [ ] [L2478] /data-catalogue
- [ ] [L2480] Display:
- [ ] [L2482] Dataset.
- [ ] [L2483] Version.
- [ ] [L2484] Source.
- [ ] [L2485] Instruments.
- [ ] [L2486] Date range.
- [ ] [L2487] Frequency.
- [ ] [L2488] Quality.
- [ ] [L2489] Lineage.
- [ ] [L2490] Backtest consumers.
- [ ] [L2491] Model consumers.
- [ ] [L2492] Report consumers.

### 21.8 System Health

- [ ] [L2496] Route:
- [ ] [L2498] /system-health
- [ ] [L2500] Display actual health:
- [ ] [L2502] API.
- [ ] [L2503] PostgreSQL.
- [ ] [L2504] Redis.
- [ ] [L2505] Object storage.
- [ ] [L2506] Data worker.
- [ ] [L2507] Quant worker.
- [ ] [L2508] Report engine.
- [ ] [L2509] Workflow engine.
- [ ] [L2510] FRED.
- [ ] [L2511] SEC.
- [ ] [L2512] OpenFIGI.
- [ ] [L2513] Market provider.
- [ ] [L2514] IBKR agent.
- [ ] [L2515] Local file agent.
- [ ] [L2516] Backups.

### 22. MILESTONE 17 - GLOBAL SEARCH AND FULL FUNCTION REGISTRY

- [ ] [L2522] Preserve and complete the full global search architecture.
- [ ] [L2524] Search:
- [ ] [L2526] Securities.
- [ ] [L2527] Functions.
- [ ] [L2528] Indicators.
- [ ] [L2529] Portfolios.
- [ ] [L2530] Positions.
- [ ] [L2531] Strategies.
- [ ] [L2532] Backtests.
- [ ] [L2533] Research.
- [ ] [L2534] Datasets.
- [ ] [L2535] Reports.
- [ ] [L2536] Jobs.
- [ ] [L2537] Alerts.
- [ ] [L2538] Workspaces.
- [ ] [L2540] Support:
- [ ] [L2542] Exact symbol.
- [ ] [L2543] Exact mnemonic.
- [ ] [L2544] Fuzzy typo matching.
- [ ] [L2545] Active-security context.
- [ ] [L2546] Multiple-security context.
- [ ] [L2547] Favourites.
- [ ] [L2548] Recent functions.
- [ ] [L2549] Portfolio holding boost.
- [ ] [L2550] Watchlist boost.
- [ ] [L2551] Natural-language intent routing.
- [ ] [L2552] Ctrl+K.
- [ ] [L2553] Slash shortcut.
- [ ] [L2554] Keyboard selection.
- [ ] [L2555] Ctrl+Enter new tab.
- [ ] [L2557] Register every function from the original KnK Master Function & UI Specification.
- [ ] [L2560] Do not mark placeholder functions AVAILABLE.
- [ ] [L2562] Statuses:
- [ ] [L2564] AVAILABLE
- [ ] [L2565] DEMO_AVAILABLE
- [ ] [L2566] PROVIDER_REQUIRED
- [ ] [L2567] IN_DEVELOPMENT

### 23. MILESTONE 18 - DATABASE EXPANSION

- [ ] [L2573] Implement full migrations for:
- [ ] [L2575] AUTH:
- [ ] [L2577] users
- [ ] [L2578] user_sessions
- [ ] [L2579] totp_settings
- [ ] [L2580] recovery_codes
- [ ] [L2581] login_attempts
- [ ] [L2582] trusted_devices
- [ ] [L2584] REFERENCE:
- [ ] [L2586] instruments
- [ ] [L2587] instrument_identifiers
- [ ] [L2588] exchanges
- [ ] [L2589] currencies
- [ ] [L2590] benchmarks
- [ ] [L2591] provider_instrument_mappings
- [ ] [L2593] PORTFOLIO:
- [ ] [L2595] portfolios
- [ ] [L2596] portfolio_accounts
- [ ] [L2597] portfolio_transactions
- [ ] [L2598] portfolio_cash_balances
- [ ] [L2599] position_lots
- [ ] [L2600] portfolio_positions
- [ ] [L2601] position_valuations
- [ ] [L2602] portfolio_valuation_runs
- [ ] [L2603] nav_snapshots
- [ ] [L2604] daily_returns
- [ ] [L2605] benchmark_returns
- [ ] [L2606] capital_flows
- [ ] [L2607] portfolio_income
- [ ] [L2608] portfolio_fees
- [ ] [L2609] portfolio_liabilities
- [ ] [L2610] target_allocations
- [ ] [L2611] rebalance_recommendations
- [ ] [L2613] DATA:
- [ ] [L2615] uploaded_files
- [ ] [L2616] file_hashes
- [ ] [L2617] mapping_profiles
- [ ] [L2618] mapping_profile_versions
- [ ] [L2619] datasets
- [ ] [L2620] dataset_versions
- [ ] [L2621] dataset_columns
- [ ] [L2622] dataset_lineage
- [ ] [L2623] import_runs
- [ ] [L2624] ingestion_jobs
- [ ] [L2625] ingestion_job_runs
- [ ] [L2626] raw_objects
- [ ] [L2627] quarantine_records
- [ ] [L2628] data_quality_issues
- [ ] [L2630] PROVIDERS:
- [ ] [L2632] provider_connections
- [ ] [L2633] provider_health_snapshots
- [ ] [L2634] provider_request_logs
- [ ] [L2635] provider_rate_limit_states
- [ ] [L2636] source_precedence_rules
- [ ] [L2637] field_source_values
- [ ] [L2638] source_conflicts
- [ ] [L2639] source_overrides
- [ ] [L2641] MACRO:
- [ ] [L2643] macro_series
- [ ] [L2644] macro_observations
- [ ] [L2645] macro_releases
- [ ] [L2646] macro_vintages
- [ ] [L2648] MARKET:
- [ ] [L2650] price_bars
- [ ] [L2651] latest_quotes
- [ ] [L2652] fx_rates
- [ ] [L2653] corporate_actions
- [ ] [L2654] dividends
- [ ] [L2655] splits
- [ ] [L2657] BROKER AND TRADE:
- [ ] [L2659] broker_agents
- [ ] [L2660] broker_agent_sessions
- [ ] [L2661] broker_accounts
- [ ] [L2662] broker_snapshots
- [ ] [L2663] broker_cash_balances
- [ ] [L2664] broker_positions
- [ ] [L2665] broker_orders_readonly
- [ ] [L2666] broker_executions
- [ ] [L2667] broker_fills
- [ ] [L2668] broker_commissions
- [ ] [L2669] trade_events
- [ ] [L2670] trade_reviews
- [ ] [L2671] trade_risk_snapshots
- [ ] [L2672] reconciliation_runs
- [ ] [L2673] reconciliation_breaks
- [ ] [L2675] QUANT:
- [ ] [L2677] strategy_definitions
- [ ] [L2678] strategy_versions
- [ ] [L2679] strategy_parameters
- [ ] [L2680] strategy_runs
- [ ] [L2681] signals
- [ ] [L2682] factor_definitions
- [ ] [L2683] factor_runs
- [ ] [L2684] factor_values
- [ ] [L2685] backtest_runs
- [ ] [L2686] backtest_metrics
- [ ] [L2687] backtest_equity_curve
- [ ] [L2688] backtest_positions
- [ ] [L2689] backtest_trades
- [ ] [L2690] walk_forward_runs
- [ ] [L2691] monte_carlo_runs
- [ ] [L2692] model_definitions
- [ ] [L2693] model_versions
- [ ] [L2694] model_runs
- [ ] [L2695] model_artifacts
- [ ] [L2696] experiment_runs
- [ ] [L2698] RISK:
- [ ] [L2700] risk_policies
- [ ] [L2701] risk_limits
- [ ] [L2702] risk_snapshots
- [ ] [L2703] risk_breaches
- [ ] [L2704] stress_scenarios
- [ ] [L2705] stress_runs
- [ ] [L2706] stress_results
- [ ] [L2707] hedge_instruments
- [ ] [L2708] hedge_recommendations
- [ ] [L2709] hedge_recommendation_items
- [ ] [L2711] RESEARCH:
- [ ] [L2713] watchlists
- [ ] [L2714] watchlist_items
- [ ] [L2715] research_notes
- [ ] [L2716] investment_theses
- [ ] [L2717] thesis_scenarios
- [ ] [L2718] thesis_catalysts
- [ ] [L2719] thesis_risks
- [ ] [L2720] thesis_sources
- [ ] [L2721] thesis_attachments
- [ ] [L2722] decision_journal
- [ ] [L2723] idea_records
- [ ] [L2725] REPORTS:
- [ ] [L2727] report_templates
- [ ] [L2728] report_requests
- [ ] [L2729] generated_reports
- [ ] [L2730] report_sources
- [ ] [L2732] OPERATIONS:
- [ ] [L2734] system_health_snapshots
- [ ] [L2735] alerts
- [ ] [L2736] alert_deliveries
- [ ] [L2737] audit_logs
- [ ] [L2738] workspaces
- [ ] [L2739] workspace_tabs
- [ ] [L2740] recent_commands
- [ ] [L2741] favourite_functions
- [ ] [L2743] Requirements:
- [ ] [L2745] UUID identifiers.
- [ ] [L2746] Foreign keys.
- [ ] [L2747] Unique constraints.
- [ ] [L2748] Check constraints.
- [ ] [L2749] Query indexes.
- [ ] [L2750] UTC timestamps.
- [ ] [L2751] NUMERIC fields for money.
- [ ] [L2752] No secrets in normal tables.
- [ ] [L2753] Upgrade and downgrade support.
- [ ] [L2754] Migration tests.

### 24. MILESTONE 19 - BACKGROUND JOBS AND REDIS

- [ ] [L2760] Fix Redis connectivity and make asynchronous work operational.
- [ ] [L2762] Job states:
- [ ] [L2764] PENDING
- [ ] [L2765] QUEUED
- [ ] [L2766] RUNNING
- [ ] [L2767] RETRYING
- [ ] [L2768] SUCCEEDED
- [ ] [L2769] FAILED
- [ ] [L2770] CANCELLED
- [ ] [L2772] Every job records:
- [ ] [L2774] Job ID.
- [ ] [L2775] Type.
- [ ] [L2776] Parameters.
- [ ] [L2777] Provider.
- [ ] [L2778] Dataset.
- [ ] [L2779] Created.
- [ ] [L2780] Started.
- [ ] [L2781] Finished.
- [ ] [L2782] Worker.
- [ ] [L2783] Progress.
- [ ] [L2784] Stage.
- [ ] [L2785] Records received.
- [ ] [L2786] Records accepted.
- [ ] [L2787] Records rejected.
- [ ] [L2788] Retry count.
- [ ] [L2789] Error type.
- [ ] [L2790] Error details.
- [ ] [L2791] Correlation ID.
- [ ] [L2793] Jobs:
- [ ] [L2795] FRED refresh.
- [ ] [L2796] SEC refresh.
- [ ] [L2797] OpenFIGI mapping.
- [ ] [L2798] File ingestion.
- [ ] [L2799] Dataset validation.
- [ ] [L2800] Dataset import.
- [ ] [L2801] Portfolio valuation.
- [ ] [L2802] Performance calculation.
- [ ] [L2803] Risk calculation.
- [ ] [L2804] Stress test.
- [ ] [L2805] Backtest.
- [ ] [L2806] Factor run.
- [ ] [L2807] Model training.
- [ ] [L2808] Walk-forward.
- [ ] [L2809] Monte Carlo.
- [ ] [L2810] Report generation.
- [ ] [L2811] Backup.
- [ ] [L2812] Stale-data scan.
- [ ] [L2813] Reconciliation.
- [ ] [L2815] Create real-time progress using Server-Sent Events.
- [ ] [L2817] The browser must display:
- [ ] [L2819] Queued.
- [ ] [L2820] Running.
- [ ] [L2821] Percentage.
- [ ] [L2822] Stage.
- [ ] [L2823] Completion.
- [ ] [L2824] Failure.
- [ ] [L2825] Retry.

### 25. MILESTONE 20 - MONITORING AND PERFORMANCE

- [ ] [L2831] Implement:
- [ ] [L2833] /health/live
- [ ] [L2834] /health/ready
- [ ] [L2835] /metrics
- [ ] [L2837] Prometheus metrics:
- [ ] [L2839] Request count.
- [ ] [L2840] Request latency.
- [ ] [L2841] Error count.
- [ ] [L2842] Database pool.
- [ ] [L2843] Redis state.
- [ ] [L2844] Object-storage state.
- [ ] [L2845] Worker state.
- [ ] [L2846] Job count.
- [ ] [L2847] Job duration.
- [ ] [L2848] Backtest duration.
- [ ] [L2849] Ingestion rows.
- [ ] [L2850] Rejected rows.
- [ ] [L2851] Provider latency.
- [ ] [L2852] Provider failures.
- [ ] [L2853] Rate limits.
- [ ] [L2854] Data freshness.
- [ ] [L2855] Risk-calculation failures.
- [ ] [L2856] Report-generation failures.
- [ ] [L2857] Authentication failures.
- [ ] [L2859] Grafana dashboards:
- [ ] [L2861] 1. Platform Overview.
- [ ] [L2862] 2. API Performance.
- [ ] [L2863] 3. Data Ingestion.
- [ ] [L2864] 4. Quant Jobs.
- [ ] [L2865] 5. Provider Health.
- [ ] [L2866] 6. Portfolio Operations.
- [ ] [L2867] 7. Risk Monitoring.
- [ ] [L2868] 8. Security Events.
- [ ] [L2870] Performance targets after local warm-up:
- [ ] [L2872] Search under 150ms.
- [ ] [L2873] Portfolio summary under 250ms.
- [ ] [L2874] Overview under 500ms where dependencies are healthy.
- [ ] [L2875] Transaction save under 500ms.
- [ ] [L2876] NAV calculation under 2 seconds for KNK_MAIN.
- [ ] [L2877] Risk calculation under 5 seconds for KNK_MAIN.
- [ ] [L2878] CSV preview under 3 seconds for normal files.
- [ ] [L2879] Backtests asynchronous.
- [ ] [L2880] No API blocking from backtests.
- [ ] [L2882] Display measured latency truthfully.

### 26. SECURITY AND ABSOLUTE NO-EXECUTION RULE

- [ ] [L2888] The application must have no broker execution capability.
- [ ] [L2890] Forbidden:
- [ ] [L2892] placeOrder cancelOrder reqGlobalCancel transmitOrder modifyOrder submitOrder executeTrade autoRebalance autoHedge
- [ ] [L2902] No backend route may submit an order.
- [ ] [L2904] No frontend button may submit an order.
- [ ] [L2906] No TradingView webhook may submit an order.
- [ ] [L2908] No hedge recommendation may submit an order.
- [ ] [L2910] No AI action may submit an order.
- [ ] [L2912] The IBKR adapter may read:
- [ ] [L2914] Account summary.
- [ ] [L2915] Positions.
- [ ] [L2916] Cash.
- [ ] [L2917] Open orders for monitoring.
- [ ] [L2918] Executions.
- [ ] [L2919] Fills.
- [ ] [L2920] Commissions.
- [ ] [L2921] P&L.
- [ ] [L2922] Contract details.
- [ ] [L2924] It must not write.
- [ ] [L2926] Create repository security tests that fail if forbidden broker execution logic is introduced.

### 27. SUBSTANTIVE TEST IMPLEMENTATION

- [ ] [L2933] At least 7,000 of the required 25,000 new lines must be substantive tests.

### 27.1 Portfolio tests

- [ ] [L2937] Test:
- [ ] [L2939] SGD 70,000 opening contribution.
- [ ] [L2940] Buy.
- [ ] [L2941] Sell.
- [ ] [L2942] Partial sale.
- [ ] [L2943] Full sale.
- [ ] [L2944] Short.
- [ ] [L2945] Cover.
- [ ] [L2946] Weighted-average cost.
- [ ] [L2947] FIFO.
- [ ] [L2948] Commission.
- [ ] [L2949] Fee.
- [ ] [L2950] Dividend.
- [ ] [L2951] Interest.
- [ ] [L2952] Tax.
- [ ] [L2953] Split.
- [ ] [L2954] FX conversion.
- [ ] [L2955] Multi-currency cash.
- [ ] [L2956] Position calculation.
- [ ] [L2957] Market value.
- [ ] [L2958] Realised P&L.
- [ ] [L2959] Unrealised P&L.
- [ ] [L2960] NAV.
- [ ] [L2961] Daily P&L.
- [ ] [L2962] Capital flows.
- [ ] [L2963] TWR.
- [ ] [L2964] XIRR.
- [ ] [L2965] Stale prices.
- [ ] [L2966] Missing prices.
- [ ] [L2967] Missing FX.
- [ ] [L2968] Broker/reference separation.

### 27.2 Performance tests

- [ ] [L2972] Test:
- [ ] [L2974] Daily returns.
- [ ] [L2975] Chain linking.
- [ ] [L2976] MTD.
- [ ] [L2977] QTD.
- [ ] [L2978] YTD.
- [ ] [L2979] CAGR.
- [ ] [L2980] Volatility.
- [ ] [L2981] Sharpe.
- [ ] [L2982] Sortino.
- [ ] [L2983] Calmar.
- [ ] [L2984] Drawdown.
- [ ] [L2985] Recovery.
- [ ] [L2986] Beta.
- [ ] [L2987] Alpha.
- [ ] [L2988] Tracking error.
- [ ] [L2989] Information ratio.
- [ ] [L2990] Upside/downside capture.
- [ ] [L2991] Insufficient history.

### 27.3 File-ingestion tests

- [ ] [L2995] Test:
- [ ] [L2997] CSV.
- [ ] [L2998] XLSX.
- [ ] [L2999] Parquet.
- [ ] [L3000] JSON.
- [ ] [L3001] File hashing.
- [ ] [L3002] Duplicate detection.
- [ ] [L3003] Filename parsing.
- [ ] [L3004] Mapping profiles.
- [ ] [L3005] Header aliases.
- [ ] [L3006] Date parsing.
- [ ] [L3007] Numeric parsing.
- [ ] [L3008] Currency.
- [ ] [L3009] Invalid OHLC.
- [ ] [L3010] Negative volume.
- [ ] [L3011] Missing close.
- [ ] [L3012] Duplicate dates.
- [ ] [L3013] Filename/content conflict.
- [ ] [L3014] Formula injection.
- [ ] [L3015] MIME mismatch.
- [ ] [L3016] ZIP bomb protection.
- [ ] [L3017] Lineage.
- [ ] [L3018] Versioning.
- [ ] [L3019] Raw immutability.
- [ ] [L3020] Curated output.

### 27.4 Provider tests

- [ ] [L3024] Test:
- [ ] [L3026] FRED connection.
- [ ] [L3027] FRED metadata.
- [ ] [L3028] FRED observations.
- [ ] [L3029] FRED missing values.
- [ ] [L3030] FRED revisions.
- [ ] [L3031] FRED raw storage.
- [ ] [L3032] FRED backfill.
- [ ] [L3033] SEC filing metadata.
- [ ] [L3034] SEC rate control.
- [ ] [L3035] OpenFIGI batch mapping.
- [ ] [L3036] Provider health.
- [ ] [L3037] Rate-limit state.
- [ ] [L3038] Provider failure.
- [ ] [L3039] Mixed demo and connected data.
- [ ] [L3041] Use mocked external HTTP for normal test runs.

### 27.5 Risk tests

- [ ] [L3045] Test:
- [ ] [L3047] Gross exposure.
- [ ] [L3048] Net exposure.
- [ ] [L3049] Sector exposure.
- [ ] [L3050] Currency exposure.
- [ ] [L3051] Concentration.
- [ ] [L3052] HHI.
- [ ] [L3053] Volatility.
- [ ] [L3054] EWMA.
- [ ] [L3055] Covariance.
- [ ] [L3056] Correlation.
- [ ] [L3057] Beta.
- [ ] [L3058] Risk contribution.
- [ ] [L3059] Historical VaR.
- [ ] [L3060] Parametric VaR.
- [ ] [L3061] Monte Carlo VaR.
- [ ] [L3062] CVaR.
- [ ] [L3063] Limit breaches.
- [ ] [L3064] Stale-data exposure.

### 27.6 Stress and hedge tests

- [ ] [L3068] Test:
- [ ] [L3070] Market shock.
- [ ] [L3071] Sector shock.
- [ ] [L3072] Currency shock.
- [ ] [L3073] Rate shock.
- [ ] [L3074] Combined shock.
- [ ] [L3075] Position contribution.
- [ ] [L3076] Sector contribution.
- [ ] [L3077] ETF hedge.
- [ ] [L3078] Futures hedge.
- [ ] [L3079] Rounding.
- [ ] [L3080] Residual notional.
- [ ] [L3081] Beta before/after.
- [ ] [L3082] Net exposure before/after.
- [ ] [L3083] Manual-only status.

### 27.7 Backtest tests

- [ ] [L3087] Test:
- [ ] [L3089] Next-bar execution.
- [ ] [L3090] No look-ahead.
- [ ] [L3091] Cash accounting.
- [ ] [L3092] Position accounting.
- [ ] [L3093] Long-only.
- [ ] [L3094] Long-short.
- [ ] [L3095] Fees.
- [ ] [L3096] Slippage.
- [ ] [L3097] Dividends.
- [ ] [L3098] Splits.
- [ ] [L3099] Rebalancing.
- [ ] [L3100] Missing data.
- [ ] [L3101] Turnover.
- [ ] [L3102] Benchmark.
- [ ] [L3103] Strategy determinism.
- [ ] [L3104] Dataset version persistence.
- [ ] [L3105] Run cancellation.
- [ ] [L3106] Walk-forward.
- [ ] [L3107] Monte Carlo.
- [ ] [L3108] Factor IC.

### 27.8 Equity tests

- [ ] [L3112] Test:
- [ ] [L3114] Financial-period alignment.
- [ ] [L3115] Annual versus quarterly.
- [ ] [L3116] Currency scaling.
- [ ] [L3117] DCF.
- [ ] [L3118] WACC.
- [ ] [L3119] Terminal value.
- [ ] [L3120] Sensitivity.
- [ ] [L3121] Comparable medians.
- [ ] [L3122] Outlier detection.
- [ ] [L3123] Relative valuation.

### 27.9 Frontend tests

- [ ] [L3127] Test:
- [ ] [L3129] Overview API loading.
- [ ] [L3130] Portfolio KPI ribbon.
- [ ] [L3131] Positions table.
- [ ] [L3132] Add transaction.
- [ ] [L3133] Performance charts.
- [ ] [L3134] Risk dashboard.
- [ ] [L3135] Stress run.
- [ ] [L3136] Hedge recommendation.
- [ ] [L3137] Trade monitor.
- [ ] [L3138] Quant dashboard.
- [ ] [L3139] Factor Lab.
- [ ] [L3140] Data Drop.
- [ ] [L3141] Mapping.
- [ ] [L3142] Data Catalogue.
- [ ] [L3143] System Health.
- [ ] [L3144] Search.
- [ ] [L3145] Active security.
- [ ] [L3146] Workspace.
- [ ] [L3147] Tabs.
- [ ] [L3148] Demo badges.
- [ ] [L3149] File-import badges.
- [ ] [L3150] Stale warnings.
- [ ] [L3151] No broker-execution controls.

### 27.10 End-to-end tests

- [ ] [L3155] Implement complete Playwright workflows for:
- [ ] [L3157] Login.
- [ ] [L3158] TOTP.
- [ ] [L3159] Portfolio transaction.
- [ ] [L3160] NAV update.
- [ ] [L3161] File upload.
- [ ] [L3162] Mapping.
- [ ] [L3163] Import.
- [ ] [L3164] Backtest.
- [ ] [L3165] Stress test.
- [ ] [L3166] Hedge recommendation.
- [ ] [L3167] Excel report.
- [ ] [L3168] Pine export.
- [ ] [L3169] Research thesis.
- [ ] [L3170] System Health.
- [ ] [L3171] Public/private isolation.
- [ ] [L3173] Coverage targets:
- [ ] [L3175] Portfolio: 90%.
- [ ] [L3176] Performance: 90%.
- [ ] [L3177] Risk: 90%.
- [ ] [L3178] Hedge: 90%.
- [ ] [L3179] Backtesting: 85%.
- [ ] [L3180] File ingestion: 85%.
- [ ] [L3181] Provider normalisation: 85%.
- [ ] [L3182] Overall critical backend: at least 85%.
- [ ] [L3184] Do not claim coverage without executing coverage tools.

### 28. FRONTEND VISUAL TESTING

- [ ] [L3190] Create Playwright screenshot tests at:
- [ ] [L3192] 1366x768.
- [ ] [L3193] 1440x900.
- [ ] [L3194] 1920x1080.
- [ ] [L3195] 2560x1440.
- [ ] [L3197] Pages:
- [ ] [L3199] Overview.
- [ ] [L3200] Portfolio.
- [ ] [L3201] Performance.
- [ ] [L3202] Equity.
- [ ] [L3203] Quant Dashboard.
- [ ] [L3204] Risk & Trade.
- [ ] [L3205] Stress Tests.
- [ ] [L3206] Data Drop.
- [ ] [L3207] Data Catalogue.
- [ ] [L3208] Backtest Result.
- [ ] [L3209] System Health.
- [ ] [L3211] Assert:
- [ ] [L3213] No mobile layout at desktop widths.
- [ ] [L3214] No giant cards.
- [ ] [L3215] No giant heading.
- [ ] [L3216] No giant badges.
- [ ] [L3217] No blank analytical region.
- [ ] [L3218] No overlapping panels.
- [ ] [L3219] No missing status bar.
- [ ] [L3220] No unexpected horizontal overflow.
- [ ] [L3221] Compact table rows.
- [ ] [L3222] Correct black/amber theme.
- [ ] [L3223] Visible source badges.
- [ ] [L3224] Visible timestamps.

### 29. FULL ACCEPTANCE WORKFLOW

- [ ] [L3230] Do not mark this project complete until every step passes.

### 29.1 Infrastructure

- [ ] [L3234] 1. Start Docker.
- [ ] [L3235] 2. Build all services.
- [ ] [L3236] 3. PostgreSQL becomes healthy.
- [ ] [L3237] 4. Redis becomes healthy.
- [ ] [L3238] 5. Object storage becomes healthy.
- [ ] [L3239] 6. API becomes healthy.
- [ ] [L3240] 7. Data worker becomes healthy.
- [ ] [L3241] 8. Quant worker becomes healthy.
- [ ] [L3242] 9. Report engine becomes healthy.
- [ ] [L3243] 10. Frontends become healthy.
- [ ] [L3244] 11. Prometheus scrapes metrics.
- [ ] [L3245] 12. Grafana loads dashboards.

### 29.2 Portfolio

- [ ] [L3249] 13. Log in.
- [ ] [L3250] 14. Open Overview.
- [ ] [L3251] 15. See KNK_MAIN.
- [ ] [L3252] 16. See opening capital SGD 70,000.
- [ ] [L3253] 17. See current NAV reconstructed from ledger.
- [ ] [L3254] 18. Add a BUY transaction.
- [ ] [L3255] 19. Cash decreases.
- [ ] [L3256] 20. Position updates.
- [ ] [L3257] 21. NAV updates.
- [ ] [L3258] 22. P&L updates.
- [ ] [L3259] 23. Performance updates.
- [ ] [L3260] 24. Risk updates.
- [ ] [L3261] 25. Trade event appears.
- [ ] [L3262] 26. Audit event appears.
- [ ] [L3263] 27. Restart API.
- [ ] [L3264] 28. Data persist.

### 29.3 Data Drop

- [ ] [L3268] 29. Start local agent.
- [ ] [L3269] 30. Pair agent.
- [ ] [L3270] 31. Configure watched folder.
- [ ] [L3271] 32. Place AAPL price CSV into folder.
- [ ] [L3272] 33. File is detected.
- [ ] [L3273] 34. File is hashed.
- [ ] [L3274] 35. File appears in Data Drop.
- [ ] [L3275] 36. Mapping profile is suggested.
- [ ] [L3276] 37. Preview loads.
- [ ] [L3277] 38. Validation runs.
- [ ] [L3278] 39. Dataset imports.
- [ ] [L3279] 40. Dataset version is created.
- [ ] [L3280] 41. Raw file remains stored.
- [ ] [L3281] 42. Curated Parquet exists.
- [ ] [L3282] 43. Dataset appears in Catalogue.
- [ ] [L3283] 44. Re-upload is detected as duplicate.

### 29.4 Portfolio price use

- [ ] [L3287] 45. Select imported file as fallback source.
- [ ] [L3288] 46. Revalue portfolio.
- [ ] [L3289] 47. NAV uses file-import price.
- [ ] [L3290] 48. FILE IMPORT badge appears.
- [ ] [L3291] 49. As-of date appears.
- [ ] [L3292] 50. Stale file produces warning.
- [ ] [L3293] 51. Source conflict appears when another source disagrees.

### 29.5 Quant

- [ ] [L3297] 52. Open Quant Dashboard.
- [ ] [L3298] 53. Select imported dataset.
- [ ] [L3299] 54. Run moving-average backtest.
- [ ] [L3300] 55. Job enters QUEUED.
- [ ] [L3301] 56. Job enters RUNNING.
- [ ] [L3302] 57. Progress updates.
- [ ] [L3303] 58. Job succeeds.
- [ ] [L3304] 59. Results persist.
- [ ] [L3305] 60. Equity curve loads.
- [ ] [L3306] 61. Metrics load.
- [ ] [L3307] 62. Trades load.
- [ ] [L3308] 63. Dataset version is shown.
- [ ] [L3309] 64. Run Factor Lab.
- [ ] [L3310] 65. Run Walk-Forward.
- [ ] [L3311] 66. Run Monte Carlo.
- [ ] [L3312] 67. Create candidate edge.
- [ ] [L3313] 68. Mark PAPER_TESTING.
- [ ] [L3314] 69. No order is sent.

### 29.6 Equity

- [ ] [L3318] 70. Open AAPL.
- [ ] [L3319] 71. View DES.
- [ ] [L3320] 72. View FIN.
- [ ] [L3321] 73. View VAL.
- [ ] [L3322] 74. Build DCF.
- [ ] [L3323] 75. View COMP.
- [ ] [L3324] 76. Create thesis.
- [ ] [L3325] 77. Attach Koyfin source.
- [ ] [L3326] 78. Link thesis to portfolio position.
- [ ] [L3327] 79. Generate Excel equity model.
- [ ] [L3328] 80. Generate research deck.

### 29.7 Risk and trade

- [ ] [L3332] 81. Open Risk & Trade Monitor.
- [ ] [L3333] 82. View exposures.
- [ ] [L3334] 83. View risk contribution.
- [ ] [L3335] 84. View trade blotter.
- [ ] [L3336] 85. Run SPX -10% stress.
- [ ] [L3337] 86. View contribution.
- [ ] [L3338] 87. Generate beta hedge.
- [ ] [L3339] 88. See manual-review warning.
- [ ] [L3340] 89. Confirm no order is transmitted.
- [ ] [L3341] 90. Open reconciliation.
- [ ] [L3342] 91. Resolve a demo break.
- [ ] [L3343] 92. Audit history updates.

### 29.8 Reports and TradingView

- [ ] [L3347] 93. Generate portfolio Excel.
- [ ] [L3348] 94. Generate risk Excel.
- [ ] [L3349] 95. Generate backtest Excel.
- [ ] [L3350] 96. Generate Pine Script.
- [ ] [L3351] 97. Download `.pine`.
- [ ] [L3352] 98. Compare Python and Pine-compatible signals.
- [ ] [L3353] 99. Confirm no TradingView webhook executes a trade.

### 29.9 Operations

- [ ] [L3357] 100. Open System Health.
- [ ] [L3358] 101. View real API latency.
- [ ] [L3359] 102. View real Redis status.
- [ ] [L3360] 103. View real worker status.
- [ ] [L3361] 104. View real provider state.
- [ ] [L3362] 105. View local-agent heartbeat.
- [ ] [L3363] 106. View failed jobs.
- [ ] [L3364] 107. Run backup.
- [ ] [L3365] 108. Verify backup.
- [ ] [L3366] 109. Run restore test.
- [ ] [L3367] 110. Restart stack.
- [ ] [L3368] 111. Verify persistence.

### 29.10 Code and tests

- [ ] [L3372] 112. Run Python formatting.
- [ ] [L3373] 113. Run Python lint.
- [ ] [L3374] 114. Run Python type checks.
- [ ] [L3375] 115. Run backend unit tests.
- [ ] [L3376] 116. Run backend integration tests.
- [ ] [L3377] 117. Run coverage.
- [ ] [L3378] 118. Run frontend lint.
- [ ] [L3379] 119. Run TypeScript checks.
- [ ] [L3380] 120. Run frontend tests.
- [ ] [L3381] 121. Run production builds.
- [ ] [L3382] 122. Run Playwright.
- [ ] [L3383] 123. Run screenshot tests.
- [ ] [L3384] 124. Run security tests.
- [ ] [L3385] 125. Run secret scan.
- [ ] [L3386] 126. Run Docker health acceptance.
- [ ] [L3387] 127. Run LOC delta script.
- [ ] [L3388] 128. Confirm at least 25,000 qualifying new lines.
- [ ] [L3389] 129. Confirm category minimums.
- [ ] [L3390] 130. Commit.
- [ ] [L3391] 131. Push.

### 30. BUILD EVIDENCE

- [ ] [L3397] Update:
- [ ] [L3399] docs/BUILD_EVIDENCE_25K.md
- [ ] [L3401] Record actual outputs for:
- [ ] [L3403] Baseline commit.
- [ ] [L3404] Final commit.
- [ ] [L3405] Git status.
- [ ] [L3406] Database migrations.
- [ ] [L3407] Seed run.
- [ ] [L3408] Docker build.
- [ ] [L3409] Docker startup.
- [ ] [L3410] Docker service health.
- [ ] [L3411] Python lint.
- [ ] [L3412] Python type check.
- [ ] [L3413] Python tests.
- [ ] [L3414] Python coverage.
- [ ] [L3415] Frontend lint.
- [ ] [L3416] Frontend type check.
- [ ] [L3417] Frontend tests.
- [ ] [L3418] Frontend build.
- [ ] [L3419] Playwright tests.
- [ ] [L3420] Screenshot tests.
- [ ] [L3421] Security tests.
- [ ] [L3422] Secret scan.
- [ ] [L3423] Backup test.
- [ ] [L3424] Restore test.
- [ ] [L3425] Acceptance workflow.
- [ ] [L3426] LOC delta.
- [ ] [L3427] Category LOC delta.
- [ ] [L3429] For every command record:
- [ ] [L3431] Command.
- [ ] [L3432] Date.
- [ ] [L3433] Commit.
- [ ] [L3434] Exit code.
- [ ] [L3435] Summary.
- [ ] [L3436] Pass/fail.
- [ ] [L3438] Do not write "passed" without executing the command.

### 31. SOURCE CONTROL RULES

- [ ] [L3444] Use the existing remote.
- [ ] [L3446] Use the existing branch unless the repository policy requires a feature branch.
- [ ] [L3449] Do not create a new repository.
- [ ] [L3451] Do not erase history.
- [ ] [L3453] Do not force push.
- [ ] [L3455] After each milestone:
- [ ] [L3457] 1. Run milestone tests.
- [ ] [L3458] 2. Update TASKS_25K.md.
- [ ] [L3459] 3. Update STATUS_25K.md.
- [ ] [L3460] 4. Update LOC evidence.
- [ ] [L3461] 5. Commit.
- [ ] [L3462] 6. Push.
- [ ] [L3463] 7. Continue immediately.
- [ ] [L3465] Recommended commit structure:
- [ ] [L3467] feat(portfolio): complete ledger and NAV engine feat(data): implement Koyfin and external data ingestion feat(agent): add secure local folder watcher feat(providers): add FRED SEC and OpenFIGI services feat(trades): add trade monitoring and reconciliation feat(risk): complete risk stress and hedge services feat(quant): add backtesting factor and edge engines feat(equity): add financial valuation and thesis workflows feat(reports): add Excel deck and Pine exports feat(ui): complete portfolio equity quant and risk dashboards feat(ops): complete monitoring backup and health tooling test: complete production acceptance coverage

### 32. AUTONOMOUS WORK RULE

- [ ] [L3484] Do not ask for approval after every milestone.
- [ ] [L3486] Do not stop because external API credentials are absent.
- [ ] [L3488] Use:
- [ ] [L3490] Mock providers.
- [ ] [L3491] Contract tests.
- [ ] [L3492] Demo data.
- [ ] [L3493] Environment-variable integration.
- [ ] [L3494] Connection status screens.
- [ ] [L3496] Only stop for:
- [ ] [L3498] An irreversible external action.
- [ ] [L3499] A secret that cannot be mocked and is required for an external live
- [ ] [L3500] smoke test.
- [ ] [L3501] A legal or data-licensing decision.
- [ ] [L3502] A genuinely destructive action.
- [ ] [L3504] A missing FRED key is not a blocker.
- [ ] [L3506] A missing Koyfin API is not a blocker.
- [ ] [L3508] A missing IBKR connection is not a blocker.
- [ ] [L3510] The full demo and adapter implementation must continue.

### 33. NO PREMATURE COMPLETION

- [ ] [L3516] Do not return:
- [ ] [L3518] "The foundation is ready."
- [ ] [L3519] "The core architecture is complete."
- [ ] [L3520] "The remaining features can be added later."
- [ ] [L3521] "The system is production-ready" without evidence.
- [ ] [L3522] "25k lines achieved" without a count.
- [ ] [L3523] "Tests pass" without execution.
- [ ] [L3524] "FRED is integrated" if only a route exists.
- [ ] [L3525] "Backtesting works" if results are hardcoded.
- [ ] [L3526] "NAV works" if values are frontend constants.
- [ ] [L3527] "Koyfin is connected" if files are only attached and not ingested.
- [ ] [L3528] "Redis is healthy" if it is offline.
- [ ] [L3529] "IBKR is supported" if only environment variables exist.
- [ ] [L3530] "Reports work" if only placeholder download buttons exist.
- [ ] [L3532] Completion requires actual behaviour and evidence.

### 34. FINAL CODEX RESPONSE

- [ ] [L3538] At final completion report:
- [ ] [L3540] 1. Baseline commit.
- [ ] [L3541] 2. Final commit.
- [ ] [L3542] 3. Branch.
- [ ] [L3543] 4. Remote push state.
- [ ] [L3544] 5. Total new qualifying lines.
- [ ] [L3545] 6. Backend lines.
- [ ] [L3546] 7. Frontend lines.
- [ ] [L3547] 8. Worker/agent/report lines.
- [ ] [L3548] 9. Test lines.
- [ ] [L3549] 10. Database migration count.
- [ ] [L3550] 11. API route count.
- [ ] [L3551] 12. Frontend operational route count.
- [ ] [L3552] 13. Unit-test count.
- [ ] [L3553] 14. Integration-test count.
- [ ] [L3554] 15. End-to-end-test count.
- [ ] [L3555] 16. Coverage by critical package.
- [ ] [L3556] 17. Docker service health.
- [ ] [L3557] 18. Portfolio ledger implementation.
- [ ] [L3558] 19. NAV reconciliation result.
- [ ] [L3559] 20. Opening SGD 70,000 verification.
- [ ] [L3560] 21. Koyfin file-drop implementation.
- [ ] [L3561] 22. Local-agent implementation.
- [ ] [L3562] 23. Provider implementation.
- [ ] [L3563] 24. Trade-monitor implementation.
- [ ] [L3564] 25. Risk implementation.
- [ ] [L3565] 26. Stress implementation.
- [ ] [L3566] 27. Hedge implementation.
- [ ] [L3567] 28. Backtesting implementation.
- [ ] [L3568] 29. Factor/Edge implementation.
- [ ] [L3569] 30. Equity-research implementation.
- [ ] [L3570] 31. Excel/report implementation.
- [ ] [L3571] 32. TradingView implementation.
- [ ] [L3572] 33. Monitoring implementation.
- [ ] [L3573] 34. Backup and restore result.
- [ ] [L3574] 35. Remaining non-critical defects.
- [ ] [L3575] 36. External credentials still required.
- [ ] [L3576] 37. Confirmation that no broker execution capability exists.
- [ ] [L3577] 38. Confirmation that public routes cannot access private data.
- [ ] [L3578] 39. Confirmation that demo/file/live states are tracked separately.
- [ ] [L3579] 40. Exact commands required to run the completed system.
- [ ] [L3581] Do not hide failures.
- [ ] [L3583] Do not fabricate completion.

### 35. START NOW

- [ ] [L3589] Begin immediately.
- [ ] [L3591] 1. Capture baseline commit.
- [ ] [L3592] 2. Create GAP_AUDIT_25K.md.
- [ ] [L3593] 3. Create TASKS_25K.md.
- [ ] [L3594] 4. Create STATUS_25K.md.
- [ ] [L3595] 5. Create LOC counting script.
- [ ] [L3596] 6. Audit the existing portfolio engine.
- [ ] [L3597] 7. Fix the SGD 70,000 portfolio seed.
- [ ] [L3598] 8. Complete the ledger.
- [ ] [L3599] 9. Complete NAV.
- [ ] [L3600] 10. Continue through every milestone.
- [ ] [L3602] Do not stop at the audit.
- [ ] [L3604] Do not stop at portfolio UI.
- [ ] [L3606] Do not stop before 25,000 qualifying new lines.
- [ ] [L3608] Do not pad the code.
- [ ] [L3610] Build the complete operating product.
