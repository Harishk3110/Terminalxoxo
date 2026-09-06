"""Flow-adjusted drawdown episodes and calendar-day recovery durations."""

from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import date
from decimal import Decimal, localcontext
from typing import Any

from .contracts import ReturnPeriod


@dataclass
class DrawdownEpisode:
    peak_date: date
    trough_date: date
    recovery_date: date | None
    depth: Decimal
    decline_days: int
    recovery_days: int | None
    underwater_days: int
    state: str


def drawdowns(rows: Sequence[ReturnPeriod]) -> dict[str, Any]:
    if not rows or any(row.value is None for row in rows):
        return {
            "state": "INSUFFICIENT_DATA",
            "reason": "Complete return history is required",
            "series": [],
            "episodes": [],
            "maximum": None,
            "current": None,
            "longest_underwater_days": None,
        }
    index = peak = Decimal(1)
    peak_day = rows[0].start
    active: DrawdownEpisode | None = None
    episodes: list[DrawdownEpisode] = []
    series: list[dict[str, Any]] = []
    with localcontext() as context:
        context.prec = 40
        for row in rows:
            assert row.value is not None
            index *= 1 + row.value
            if index >= peak:
                if active is not None:
                    active.recovery_date = row.end
                    active.recovery_days = (row.end - active.trough_date).days
                    active.underwater_days = (row.end - active.peak_date).days
                    active.state = "RECOVERED"
                    episodes.append(active)
                    active = None
                peak = index
                peak_day = row.end
            depth = index / peak - 1 if peak else Decimal(0)
            if depth < 0:
                if active is None:
                    active = DrawdownEpisode(
                        peak_day,
                        row.end,
                        None,
                        depth,
                        (row.end - peak_day).days,
                        None,
                        (row.end - peak_day).days,
                        "ONGOING",
                    )
                if depth < active.depth:
                    active.depth = depth
                    active.trough_date = row.end
                    active.decline_days = (row.end - active.peak_date).days
                active.underwater_days = (row.end - active.peak_date).days
            series.append(
                {
                    "date": row.end,
                    "return_index": index,
                    "peak_index": peak,
                    "drawdown": depth,
                    "underwater_days": active.underwater_days if active else 0,
                }
            )
    if active is not None:
        episodes.append(active)
    return {
        "state": "AVAILABLE",
        "reason": None,
        "series": series,
        "episodes": [asdict(episode) for episode in episodes],
        "maximum": min(point["drawdown"] for point in series),
        "current": series[-1]["drawdown"],
        "longest_underwater_days": max((ep.underwater_days for ep in episodes), default=0),
    }
