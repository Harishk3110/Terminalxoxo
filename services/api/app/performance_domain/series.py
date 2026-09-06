"""Date selection and complete-period geometric aggregation; never fill missing returns."""

from collections.abc import Sequence
from dataclasses import asdict
from datetime import date
from decimal import Decimal, localcontext
from typing import Any

import pandas as pd

from .contracts import FeeBasis, Frequency, ReturnObservation, ReturnPeriod

ONE = Decimal(1)


def linked(values: Sequence[Decimal | None]) -> Decimal | None:
    if not values or any(value is None or value < -ONE for value in values):
        return None
    with localcontext() as context:
        context.prec = 40
        index = ONE
        for value in values:
            if value is not None:
                index *= ONE + value
        return index - ONE


def select_observations(
    observations: Sequence[ReturnObservation],
    start: date | None,
    end: date | None,
) -> list[ReturnObservation]:
    days = [row.day for row in observations]
    if days != sorted(set(days)):
        raise ValueError("Performance observations must have unique ascending dates")
    if start and end and start > end:
        raise ValueError("Performance start must not follow end")
    return [
        row
        for row in observations
        if (start is None or row.day >= start) and (end is None or row.day <= end)
    ]


def periods(
    observations: Sequence[ReturnObservation],
    frequency: Frequency,
    basis: FeeBasis,
) -> list[ReturnPeriod]:
    selected = select_observations(observations, None, None)
    if not selected:
        return []
    if frequency == Frequency.DAILY:
        groups = [[row] for row in selected]
    else:
        frame = pd.DataFrame(
            {"row": selected}, index=pd.DatetimeIndex([row.day for row in selected])
        )
        rule = "W-FRI" if frequency == Frequency.WEEKLY else "ME"
        groups = [
            group["row"].tolist()
            for _, group in frame.groupby(pd.Grouper(freq=rule))
            if not group.empty
        ]
    result = []
    for group in groups:
        chosen = [row.selected_return(basis) for row in group]
        reasons = list(dict.fromkeys(reason for _, reason in chosen if reason))
        first, last = pd.Timestamp(group[0].day), pd.Timestamp(group[-1].day)
        if frequency == Frequency.WEEKLY:
            boundary = last.to_period("W-FRI")
            expected = pd.bdate_range(boundary.start_time, boundary.end_time)
        elif frequency == Frequency.MONTHLY:
            boundary = last.to_period("M")
            expected = pd.bdate_range(boundary.start_time, boundary.end_time)
        else:
            expected = pd.bdate_range(first, last)
        observed = {row.day for row in group if row.day.weekday() < 5}
        complete = observed == {stamp.date() for stamp in expected} and bool(expected.size)
        complete = complete and not any(
            row.day.weekday() >= 5 and row.selected_return(basis)[0] != 0 for row in group
        )
        result.append(
            ReturnPeriod(
                group[0].day,
                group[-1].day,
                linked([value for value, _ in chosen]),
                linked([row.benchmark_return for row in group]),
                len(group),
                sum(value is None for value, _ in chosen),
                "; ".join(reasons) or None,
                complete,
            )
        )
    return result


def series_payload(rows: Sequence[ReturnPeriod]) -> list[dict[str, Any]]:
    index: Decimal | None = ONE
    benchmark: Decimal | None = ONE
    result = []
    with localcontext() as context:
        context.prec = 40
        for row in rows:
            index = (
                index * (ONE + row.value) if index is not None and row.value is not None else None
            )
            benchmark = (
                benchmark * (ONE + row.benchmark)
                if benchmark is not None and row.benchmark is not None
                else None
            )
            result.append(
                {
                    **asdict(row),
                    "state": ("AVAILABLE" if row.statistical_ready else "PARTIAL_PERIOD")
                    if row.value is not None
                    else "INCOMPLETE",
                    "return_index": index,
                    "benchmark_index": benchmark,
                }
            )
    return result


def regular_daily_dates(observations: Sequence[ReturnObservation]) -> bool:
    """A gap of five weekdays cannot be presented as a one-day risk observation."""
    for previous, current in zip(observations, observations[1:], strict=False):
        if len(pd.bdate_range(previous.day, current.day, inclusive="right")) > 1:
            return False
    return True
