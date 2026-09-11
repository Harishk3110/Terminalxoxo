# Final Acceptance

Directive: 2026-09-11. All steps below start unchecked for this final build.
Historical subsystem tests are not a substitute for this full workflow. Attach
current command evidence in BUILD_EVIDENCE.md before checking an item. Live
licensed-provider checks may remain explicitly unverified; DEMO/FILE must work.


## Infrastructure

- [ ] 1. Clone repository.
- [ ] 2. Copy `.env.example` to `.env`.
- [ ] 3. Run `docker compose up --build`.
- [ ] 4. PostgreSQL becomes healthy.
- [ ] 5. Redis becomes healthy.
- [ ] 6. MinIO becomes healthy.
- [ ] 7. API becomes healthy.
- [ ] 8. Data worker becomes healthy.
- [ ] 9. Quant worker becomes healthy.
- [ ] 10. Report engine becomes healthy.
- [ ] 11. Terminal becomes healthy.
- [ ] 12. Prometheus scrapes metrics.
- [ ] 13. Grafana loads dashboards.

## Authentication

- [ ] 14. Open terminal.
- [ ] 15. Create administrator.
- [ ] 16. Change temporary password.
- [ ] 17. Enable TOTP.
- [ ] 18. Log out.
- [ ] 19. Log in using password and TOTP.
- [ ] 20. Verify anonymous access is rejected.

## Portfolio

- [ ] 21. Open `/overview`.
- [ ] 22. See KNK_MAIN.
- [ ] 23. See opening contribution SGD 100,000.
- [ ] 24. See NAV reconstructed from ledger.
- [ ] 25. Open transactions.
- [ ] 26. Add a BUY transaction.
- [ ] 27. Cash decreases.
- [ ] 28. Position increases.
- [ ] 29. Average cost updates.
- [ ] 30. NAV recalculates.
- [ ] 31. P&L recalculates.
- [ ] 32. Performance recalculates.
- [ ] 33. Risk recalculates.
- [ ] 34. Trade event appears.
- [ ] 35. Audit event appears.
- [ ] 36. Add a partial SELL.
- [ ] 37. Realised P&L calculates.
- [ ] 38. Remaining cost basis calculates.
- [ ] 39. Add a dividend.
- [ ] 40. Cash and income update.
- [ ] 41. Restart API.
- [ ] 42. Confirm all records persist.

## Data Drop

- [ ] 43. Start local agent.
- [ ] 44. Pair agent.
- [ ] 45. Configure watched folder.
- [ ] 46. Place `AAPL_2026-09-11_prices_daily.csv`.
- [ ] 47. Agent detects file.
- [ ] 48. SHA-256 is calculated.
- [ ] 49. File appears in Data Drop.
- [ ] 50. Symbol/date/type are inferred.
- [ ] 51. Koyfin or generic price profile is suggested.
- [ ] 52. Preview loads.
- [ ] 53. Columns are mapped.
- [ ] 54. Validation runs.
- [ ] 55. Warnings are displayed.
- [ ] 56. User approves import.
- [ ] 57. Dataset version is created.
- [ ] 58. Raw file is preserved.
- [ ] 59. Curated Parquet is created.
- [ ] 60. Dataset appears in Catalogue.
- [ ] 61. Source badge shows KOYFIN FILE or FILE IMPORT.
- [ ] 62. As-of date is displayed.
- [ ] 63. Re-uploading identical file creates duplicate state.
- [ ] 64. Completed backtests remain pinned to old dataset version.

## Price and NAV source

- [ ] 65. Configure imported file as fallback price source.
- [ ] 66. Revalue portfolio.
- [ ] 67. NAV uses imported price.
- [ ] 68. NAV displays FILE IMPORT.
- [ ] 69. Stale file produces stale-data warning.
- [ ] 70. Source conflict appears when another source disagrees.
- [ ] 71. Administrator override is audited.

## Performance and Alpha

- [ ] 72. Open Performance.
- [ ] 73. View NAV and benchmark curves.
- [ ] 74. View MTD/QTD/YTD.
- [ ] 75. View drawdown.
- [ ] 76. View Beta.
- [ ] 77. View CAPM Alpha.
- [ ] 78. View Alpha confidence and p-value.
- [ ] 79. View attribution.

## Risk and Trade

- [ ] 80. Open Risk & Trade Monitor.
- [ ] 81. View exposures.
- [ ] 82. View concentration.
- [ ] 83. View correlation.
- [ ] 84. View VaR and CVaR.
- [ ] 85. View risk contributions.
- [ ] 86. View trade blotter.
- [ ] 87. View reconciliation.
- [ ] 88. Trigger a demo limit breach.
- [ ] 89. Confirm breach persists and alerts.
- [ ] 90. Confirm no order is executed.

## Stress and Hedge

- [ ] 91. Select SPX -10%.
- [ ] 92. Run stress.
- [ ] 93. Job enters queued state.
- [ ] 94. Job enters running state.
- [ ] 95. Results persist.
- [ ] 96. View position contributions.
- [ ] 97. View sector contributions.
- [ ] 98. View post-stress NAV.
- [ ] 99. Generate target-Beta hedge.
- [ ] 100. View required notional.
- [ ] 101. View rounded units.
- [ ] 102. View residual exposure.
- [ ] 103. Confirm manual-review warning.
- [ ] 104. Confirm no broker call occurs.

## Quant

- [ ] 105. Open Quant Dashboard.
- [ ] 106. Select imported dataset.
- [ ] 107. Run moving-average backtest.
- [ ] 108. Job enters queued state.
- [ ] 109. Job enters running state.
- [ ] 110. Progress updates.
- [ ] 111. Job succeeds.
- [ ] 112. Equity curve persists.
- [ ] 113. Trades persist.
- [ ] 114. Metrics persist.
- [ ] 115. Dataset version is displayed.
- [ ] 116. Run Factor Lab.
- [ ] 117. View factor coverage.
- [ ] 118. View IC.
- [ ] 119. View quantile returns.
- [ ] 120. Run walk-forward.
- [ ] 121. Run Monte Carlo.
- [ ] 122. Create candidate edge.
- [ ] 123. Mark candidate PAPER_TESTING.
- [ ] 124. Confirm no order is sent.

## Equity

- [ ] 125. Open AAPL.
- [ ] 126. View DES.
- [ ] 127. View Q.
- [ ] 128. View GP.
- [ ] 129. View TECH.
- [ ] 130. View FIN.
- [ ] 131. View VAL.
- [ ] 132. Build DCF.
- [ ] 133. View WACC.
- [ ] 134. View COMP.
- [ ] 135. Create thesis.
- [ ] 136. Link thesis to portfolio position.
- [ ] 137. Attach Koyfin source.
- [ ] 138. Generate equity-model XLSX.
- [ ] 139. Generate IC deck.

## Options

- [ ] 140. Open options chain.
- [ ] 141. View standard Greeks.
- [ ] 142. View Gamma.
- [ ] 143. View GEX.
- [ ] 144. View GEX by strike.
- [ ] 145. View GEX by expiry.
- [ ] 146. View Gamma-flip estimate.
- [ ] 147. View IV.
- [ ] 148. View skew.
- [ ] 149. Create payoff strategy.
- [ ] 150. View portfolio Greeks.
- [ ] 151. Confirm all inferred assumptions are labelled.

## TradingView

- [ ] 152. Select compatible strategy.
- [ ] 153. Generate Pine Script.
- [ ] 154. View compatibility report.
- [ ] 155. Compare Python/Pine signal dates.
- [ ] 156. Download `.pine`.
- [ ] 157. Confirm no automatic TradingView deployment claim.
- [ ] 158. Confirm webhook cannot place broker order.

## Reports

- [ ] 159. Generate portfolio XLSX.
- [ ] 160. Generate risk XLSX.
- [ ] 161. Generate backtest XLSX.
- [ ] 162. Generate portfolio PDF.
- [ ] 163. Generate strategy review deck.
- [ ] 164. Confirm source dates and states are present.

## Operations

- [ ] 165. Open System Health.
- [ ] 166. View actual API state.
- [ ] 167. View actual database state.
- [ ] 168. View actual Redis state.
- [ ] 169. View workers.
- [ ] 170. View providers.
- [ ] 171. View local-agent heartbeat.
- [ ] 172. View broker-agent state.
- [ ] 173. View failed jobs.
- [ ] 174. Run backup.
- [ ] 175. Verify backup.
- [ ] 176. Run restore test.
- [ ] 177. Restart complete stack.
- [ ] 178. Verify persistence.

## Quality

- [ ] 179. Run Python format.
- [ ] 180. Run Python lint.
- [ ] 181. Run Python type checks.
- [ ] 182. Run unit tests.
- [ ] 183. Run integration tests.
- [ ] 184. Run coverage.
- [ ] 185. Run frontend lint.
- [ ] 186. Run TypeScript checks.
- [ ] 187. Run frontend tests.
- [ ] 188. Run frontend production build.
- [ ] 189. Run Playwright.
- [ ] 190. Run visual tests.
- [ ] 191. Run security tests.
- [ ] 192. Run secret scan.
- [ ] 193. Run Docker health acceptance.
- [ ] 194. Run LOC report.
- [ ] 195. Update build evidence.
- [ ] 196. Commit.
- [ ] 197. Push to existing remote.


