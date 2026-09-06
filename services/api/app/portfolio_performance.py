"""Performance application service over immutable valuation evidence and stored analysis runs."""

from dataclasses import asdict
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import models
from .performance_domain.contracts import (
    Frequency,
    MetricResult,
    PerformanceSettings,
    ReturnObservation,
)
from .performance_domain.drawdowns import drawdowns
from .performance_domain.metrics import (
    extremes,
    measured,
    period_returns,
    rolling_statistics,
    sample_statistics,
)
from .performance_domain.money_weighted import money_weighted
from .performance_domain.series import periods, select_observations, series_payload
from .portfolio_operations import audit
from .portfolio_resources import PortfolioNotFound, PortfolioResourceService

PERFORMANCE_VERSION = "knk-performance-1.1"
METHOD = (
    "Beginning-of-period external flows; geometric linked returns; sample standard deviation (ddof=1); "
    "annual effective risk-free rate converted to the observation frequency; geometric mean benchmark capture; "
    "calendar-day drawdown durations; pyxirr ACT/365 dated investor flows. "
    "Gross returns add back recorded commissions, fees and accrued-fee changes, not taxes. "
    "Missing observations are never replaced by zero. This is an internal ledger analysis, not broker performance."
)


def snapshot_number(row: dict[str, Any], exact: str, legacy: str | None = None) -> Decimal | None:
    value = row.get(exact) if exact in row else row.get(legacy) if legacy else None
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"Invalid saved numeric field: {exact}")
    try:
        number = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError(f"Invalid saved numeric field: {exact}") from exc
    if not number.is_finite():
        raise ValueError(f"Nonfinite saved numeric field: {exact}")
    return number


def observations_from_snapshot(data: dict[str, Any]) -> list[ReturnObservation]:
    result = []
    for row in data.get("curve", []):
        result.append(
            ReturnObservation(
                day=date.fromisoformat(row["date"]),
                net_return=snapshot_number(row, "net_return_exact", "return"),
                opening_nav=snapshot_number(row, "opening_nav_exact", "opening_nav"),
                closing_nav=snapshot_number(row, "nav_exact", "equity"),
                external_flow=snapshot_number(row, "external_flow_exact", "external_flow"),
                daily_pnl=snapshot_number(row, "pnl_exact", "daily_pnl"),
                fee_expense=snapshot_number(row, "fee_expense_exact"),
                benchmark_return=snapshot_number(row, "benchmark_return_exact", "benchmark_return"),
                quality=row.get("quality", "UNAVAILABLE"),
            )
        )
    return select_observations(result, None, None)


class PortfolioPerformanceService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.resources = PortfolioResourceService(session)

    def calculate(
        self,
        key: str,
        settings: PerformanceSettings,
        valuation_run_id: str | None = None,
    ) -> dict[str, Any]:
        data = self.resources.valuation_snapshot(
            key, valuation_run_id, None if valuation_run_id else settings.end
        )
        all_rows = observations_from_snapshot(data)
        if settings.end and all_rows and settings.end > all_rows[-1].day:
            raise ValueError("Requested end exceeds the saved valuation date")
        selected = select_observations(all_rows, settings.start, settings.end)
        if settings.start and all_rows and settings.start < all_rows[0].day:
            raise ValueError("Requested start precedes available valuation history")
        prior = [row for row in all_rows if selected and row.day < selected[0].day]
        opening_day = prior[-1].day if prior else None
        daily = periods(selected, Frequency.DAILY, settings.fee_basis)
        monthly = periods(selected, Frequency.MONTHLY, settings.fee_basis)
        chosen = periods(selected, settings.frequency, settings.fee_basis)
        dd = drawdowns(daily)
        metrics = period_returns(selected, settings)
        metrics.update(sample_statistics(chosen, selected, settings))
        metrics.update(money_weighted(selected, opening_day, settings.fee_basis))
        metrics.update(extremes(daily, "day"))
        metrics.update(extremes(monthly, "month"))
        metrics["daily_pnl"] = measured(
            selected[-1].daily_pnl if selected else None, 1 if selected else 0, "CURRENCY"
        )
        for name, field in (
            ("max_drawdown", "maximum"),
            ("current_drawdown", "current"),
            ("drawdown_duration", "longest_underwater_days"),
        ):
            metrics[name] = measured(
                dd[field], len(selected), "DAYS" if name == "drawdown_duration" else "RETURN"
            )
        recovered = [
            row["recovery_days"] for row in dd["episodes"] if row["recovery_days"] is not None
        ]
        metrics["recovery_duration"] = (
            measured(max(recovered), len(recovered), "DAYS")
            if recovered
            else MetricResult.unavailable(0, "No completed recovery episode", "DAYS")
        )
        cagr = metrics["cagr"].value
        maximum = dd["maximum"]
        metrics["calmar"] = measured(
            float(cagr) / abs(float(maximum)) if cagr is not None and maximum else None,
            len(selected),
            "RATIO",
        )
        metrics["since_inception"] = (
            metrics["twr"]
            if selected and selected[0].day == all_rows[0].day
            else MetricResult.unavailable(len(selected), "Selected range excludes inception")
        )
        legacy = any("net_return_exact" not in row for row in data.get("curve", []))
        warnings = []
        if legacy:
            warnings.append(
                "Legacy snapshot: source curve amounts and returns may already be rounded"
            )
        if settings.fee_basis == "GROSS" and any(row.fee_expense is None for row in selected):
            warnings.append("Gross metrics unavailable where saved fee expense is absent")
        payload = {
            "implementation_state": "IN DEVELOPMENT",
            "portfolio_id": data["portfolio"]["id"],
            "base_currency": data["portfolio"]["base_currency"],
            "valuation_run_id": data["valuation_run_id"],
            "calculation_version": PERFORMANCE_VERSION,
            "valuation_version": data["calculation_version"],
            "calculated_at": data["calculated_at"],
            "source_quality": data["quality"],
            "source_precision": "LEGACY_ROUNDED" if legacy else "DECIMAL",
            "settings": settings.model_dump(mode="json"),
            "methodology": METHOD,
            "warnings": warnings,
            "start": selected[0].day if selected else None,
            "end": selected[-1].day if selected else None,
            "state": "AVAILABLE" if metrics["twr"].value is not None else "INSUFFICIENT_DATA",
            "summary": {name: asdict(metric) for name, metric in metrics.items()},
            "series": series_payload(chosen),
            "monthly": series_payload(monthly),
            "drawdowns": dd,
            "rolling": rolling_statistics(
                chosen, settings.rolling_window, settings.periods_per_year
            ),
        }
        return cast(dict[str, Any], jsonable_encoder(payload, custom_encoder={Decimal: str}))

    def save(
        self,
        key: str,
        settings: PerformanceSettings,
        valuation_run_id: str | None,
        actor: str | None,
    ) -> dict[str, Any]:
        started = datetime.now(UTC)
        result = self.calculate(key, settings, valuation_run_id)
        finished = datetime.now(UTC)
        run = models.AnalysisRun(
            kind="PORTFOLIO_PERFORMANCE",
            name=f"Portfolio performance / {key}",
            status="SUCCEEDED",
            parameters={
                "portfolio_id": result["portfolio_id"],
                "valuation_run_id": result["valuation_run_id"],
                "settings": settings.model_dump(mode="json"),
                "version": PERFORMANCE_VERSION,
            },
            result=result,
            started_at=started,
            finished_at=finished,
            history=[
                {"state": "RUNNING", "at": started.isoformat()},
                {"state": "SUCCEEDED", "at": finished.isoformat()},
            ],
        )
        self.session.add(run)
        self.session.flush()
        audit(
            self.session,
            "PORTFOLIO_PERFORMANCE_CALCULATED",
            "analysis_run",
            run.id,
            {
                "portfolio_id": result["portfolio_id"],
                "valuation_run_id": result["valuation_run_id"],
                "version": PERFORMANCE_VERSION,
                "state": result["state"],
            },
            actor,
        )
        return {"analysis_run_id": run.id, **result}

    def saved(self, key: str, run_id: str) -> dict[str, Any]:
        portfolio, _ = self.resources.resolve(key)
        run = self.session.scalar(
            select(models.AnalysisRun).where(
                models.AnalysisRun.id == run_id,
                models.AnalysisRun.kind == "PORTFOLIO_PERFORMANCE",
            )
        )
        if run is None or run.parameters.get("portfolio_id") != portfolio.id or run.result is None:
            raise PortfolioNotFound("Performance run not found in portfolio")
        return {"analysis_run_id": run.id, **run.result}
