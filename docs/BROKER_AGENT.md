# Broker Agent

The broker agent is a local Windows-compatible read-only bridge. It exposes health, pairing, status, and account snapshot interfaces in version 0.1.

It is designed for outbound communication to the cloud backend and local connectivity to TWS or IB Gateway. Device tokens must be revocable and account identifiers should be redacted from logs.
