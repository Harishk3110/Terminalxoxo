# Equity Desk

Route /equity joins main-portfolio holdings with security coverage, weights,
selected price/source, thesis counts and latest price-file provenance.
Selecting a security opens the existing DES/GP/FIN/valuation/technical views.
The research workspace retains private notes and watchlist controls.

Imported fundamental statements preserve actual/estimate and frequency rather
than merging them into synthetic annuals. Supported standard metrics are
converted to currency/share millions for existing statement and DCF views;
unrecognized units are not guessed. Incomplete imported statements make DCF
unavailable instead of using demo fields.

SEC filings, earnings and other provider-backed coverage remain PROVIDER
REQUIRED unless independently configured. The seeded financial statements are
synthetic demonstrations, not claims about actual company financials.
