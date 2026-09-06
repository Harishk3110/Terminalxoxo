# Gamma and Exposure

Options calculations are private, saved AnalysisRuns pinned to a hash-verified
chain version, observation cutoff, spot source or explicit user assumption,
rates, dividend yield, expiry filter, age threshold and inventory convention.
They never create trades or infer an actual dealer book from open interest.

## Pricing and Units

The engine uses vollib 1.0.11 Black-Scholes-Merton and its implied-volatility
solver. European continuous-yield pricing uses ACT/365 time in years. American
contracts are not priced unless the user explicitly accepts the European
approximation; early exercise, discrete dividends and assignment are not modeled.
Observed provider Greeks remain separate and require declared STANDARD units.

Delta is per underlying unit. Gamma is delta change per one currency-unit spot
move. Contract gamma multiplies gamma by the contract multiplier. Dollar gamma
multiplies contract gamma by spot squared. Theta is per calendar day; vega and
rho are per one percentage-point volatility/rate move. Higher-order Greeks use
central finite differences and carry explicit units; near-expiry and low-volatility
results can be numerically unstable. They are estimates, not hedge instructions.

Signed GEX for a one-percent move = OI * gamma * multiplier * spot^2 * 0.01 * sign.
Signed DEX = OI * delta * multiplier * spot * sign.
Dealer-short assigns -1 to all contracts. Neutral is unsigned inventory exposure,
not a claim that dealers are flat. Call-positive/put-negative is an explicit
alternative assumption. No convention identifies real dealer ownership.

Strike/expiry totals sum eligible contracts. Missing OI, stale or expired quotes,
unsupported pricing and missing Greeks are excluded and counted, never replaced
with zero. Zero reported OI is a legitimate zero exposure. Confidence is LOW
because inventory is unobserved, even with complete chain coverage.

The 41-point spot profile holds IV, rates, OI and time fixed. Its BSM coverage may
differ from provider-Greek current-spot coverage. Gamma flip is an interpolated
sign crossing only inside the selected range; no crossing means unavailable.
Walls rank absolute strike exposure. Max pain is a static OI settlement-payout
minimum, not a price forecast. Expected move is ATM IV * spot * sqrt(time).
The surface is observed strike/expiry IV, without invented interpolation.
25-delta skew uses nearest observed deltas within 0.10 tolerance, otherwise
INSUFFICIENT DATA; it is not an interpolated volatility calibration.

## Owned Positions

Position Greeks use signed contract quantities and multipliers, never market OI.
The internal-book view pins a valuation run and includes only the selected
underlying and matched option symbols. Other option symbols are listed as
excluded. It is not a consolidated multi-currency portfolio risk engine.
Hypothetical legs are separate from ledger transactions. Single-expiry payoff
uses explicit entry premiums or marked quotes and excludes fees/assignment.
Mixed-expiry payoff is unavailable instead of assuming common settlement.

Reference: https://vollib.org/documentation.html
