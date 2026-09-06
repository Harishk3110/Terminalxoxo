"""Dated investor cash flows solved by pyxirr, with explicit unsupported outcomes."""

import math
from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

import pyxirr

from .contracts import FeeBasis, MetricResult, ReturnObservation
from .metrics import measured


def money_weighted(
    observations: Sequence[ReturnObservation],
    opening_date: date | None,
    basis: FeeBasis,
) -> dict[str, MetricResult]:
    count = len(observations)
    reason = None
    if not observations:
        reason = "No observations in requested range"
    elif any(row.external_flow is None or row.closing_nav is None for row in observations):
        reason = "Cash flows and valuations must be complete"
    elif observations[0].opening_nav is None:
        reason = "Opening NAV is unavailable"
    elif basis == FeeBasis.GROSS and any(row.fee_expense is None for row in observations):
        reason = "Recorded fee expenses are required for gross money-weighted returns"
    if reason:
        return {key: MetricResult.unavailable(count, reason) for key in ("mwr", "xirr")}
    start = opening_date or observations[0].day
    end = observations[-1].day
    if start > observations[0].day:
        raise ValueError("Opening valuation date must not follow the first return date")
    days = (end - start).days
    if days <= 0:
        return {
            key: MetricResult.unavailable(count, "Dated flows need a positive elapsed period")
            for key in ("mwr", "xirr")
        }
    flows: dict[date, Decimal] = defaultdict(Decimal)
    flows[start] -= observations[0].opening_nav or Decimal(0)
    for row in observations:
        flows[row.day] -= row.external_flow or Decimal(0)
        if basis == FeeBasis.GROSS:
            flows[row.day] += row.fee_expense or Decimal(0)
    flows[end] += observations[-1].closing_nav or Decimal(0)
    payments = [(day, float(amount)) for day, amount in sorted(flows.items()) if amount]
    amounts = [amount for _, amount in payments]
    if not all(math.isfinite(amount) for amount in amounts):
        reason = "Cash flows exceed solver numerical bounds"
    elif not any(amount < 0 for amount in amounts) or not any(amount > 0 for amount in amounts):
        reason = "Solver needs both investor contributions and distributions"
    elif not pyxirr.is_conventional_cash_flow(amounts):
        reason = "Non-conventional cash flows may have multiple roots; no unique IRR is reported"
    if reason:
        return {key: MetricResult.unavailable(count, reason) for key in ("mwr", "xirr")}
    try:
        annual = pyxirr.xirr(payments)
        if annual is None or not math.isfinite(annual) or annual <= -1:
            raise ValueError("No finite IRR root")
        actual = math.expm1(math.log1p(annual) * days / 365)
    except (ValueError, OverflowError, pyxirr.InvalidPaymentsError):
        return {
            key: MetricResult.unavailable(count, "No finite IRR solution for the dated cash flows")
            for key in ("mwr", "xirr")
        }
    return {
        "mwr": measured(actual, count),
        "xirr": measured(annual, count)
        if days >= 365
        else MetricResult.unavailable(
            count, "Annual XIRR requires one year; MWR describes the actual period"
        ),
    }
