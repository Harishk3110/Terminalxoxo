"""HAC-robust return regressions; excess returns are not evidence of skill."""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
import pandas as pd
import statsmodels.api as sm
from pydantic import BaseModel, ConfigDict, Field


class AlphaSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    annual_periods: Literal[12, 52, 252] = 252
    minimum_observations: int = Field(default=60, ge=20, le=1000)
    hac_lags: int = Field(default=5, ge=0, le=63)
    rolling_window: int = Field(default=60, ge=20, le=1000)
    confidence: float = Field(default=0.95, ge=0.8, le=0.999, allow_inf_nan=False)


def finite(value):
    return float(value) if value is not None and np.isfinite(value) else None


def regression(returns: pd.Series, factors: pd.DataFrame, settings: AlphaSettings) -> dict:
    if (
        not returns.index.equals(factors.index)
        or not returns.index.is_unique
        or not returns.index.is_monotonic_increasing
    ):
        raise ValueError("Regression dates must be uniquely aligned and chronological")
    if factors.columns.has_duplicates or not 1 <= len(factors.columns) <= 12 or "const" in factors:
        raise ValueError("Supply one to twelve uniquely named factors, without an intercept column")
    y, x = returns.to_numpy(dtype=float), factors.to_numpy(dtype=float)
    count = len(y)
    result = {
        "state": "INSUFFICIENT_DATA",
        "observations": count,
        "alpha_per_period": None,
        "annualised_alpha": None,
        "confidence_interval": None,
        "annualised_confidence_interval": None,
        "p_value": None,
        "r_squared": None,
        "adjusted_r_squared": None,
        "coefficients": [],
        "reason": None,
        "settings": settings.model_dump(),
        "methodology": "OLS intercept on excess returns; Bartlett HAC covariance with finite-sample correction and t inference. Arithmetic annualisation of intercept and confidence interval. Not a compound return or a proof of skill.",
    }
    if count < max(settings.minimum_observations, len(factors.columns) + 3, settings.hac_lags + 2):
        result["reason"] = (
            "Insufficient complete observations for the selected regression and HAC lags"
        )
        return result
    if not np.isfinite(y).all() or not np.isfinite(x).all():
        result["reason"] = "Missing or nonfinite observations are not dropped from a regression"
        return result
    design = sm.add_constant(x, has_constant="add")
    if np.linalg.matrix_rank(design) < design.shape[1]:
        result["reason"] = "Constant or collinear factors do not identify unique coefficients"
        return result
    fit = sm.OLS(y, design, missing="raise").fit(
        cov_type="HAC", cov_kwds={"maxlags": settings.hac_lags, "use_correction": True}, use_t=True
    )
    interval = fit.conf_int(alpha=1 - settings.confidence)
    names = ["alpha", *map(str, factors.columns)]
    result.update(
        {
            "state": "AVAILABLE",
            "alpha_per_period": finite(fit.params[0]),
            "annualised_alpha": finite(fit.params[0] * settings.annual_periods),
            "confidence_interval": [finite(value) for value in interval[0]],
            "annualised_confidence_interval": [
                finite(value * settings.annual_periods) for value in interval[0]
            ],
            "p_value": finite(fit.pvalues[0]),
            "r_squared": finite(fit.rsquared) if np.var(y) > 0 else None,
            "adjusted_r_squared": finite(fit.rsquared_adj) if np.var(y) > 0 else None,
            "coefficients": [
                {
                    "factor": name,
                    "coefficient": finite(fit.params[i]),
                    "standard_error": finite(fit.bse[i]),
                    "t_statistic": finite(fit.tvalues[i]),
                    "p_value": finite(fit.pvalues[i]),
                    "lower": finite(interval[i, 0]),
                    "upper": finite(interval[i, 1]),
                }
                for i, name in enumerate(names)
            ],
            "start": str(returns.index[0]),
            "end": str(returns.index[-1]),
        }
    )
    return result


def alpha_analysis(
    returns: pd.Series,
    factors: pd.DataFrame,
    settings: AlphaSettings,
    risk_free: float | pd.Series = 0.0,
    benchmark: pd.Series | None = None,
) -> dict:
    if isinstance(risk_free, pd.Series):
        if not returns.index.equals(risk_free.index):
            raise ValueError("Risk-free observations must align exactly")
        rf = risk_free
    else:
        if not math.isfinite(risk_free) or risk_free <= -1 or risk_free > 1:
            raise ValueError("Invalid annual effective risk-free rate")
        rf = math.expm1(math.log1p(risk_free) / settings.annual_periods)
    excess = returns - rf
    result = regression(excess, factors, settings)
    rolling = []
    for end in range(settings.rolling_window, len(returns) + 1):
        begin = end - settings.rolling_window
        calculated = regression(excess.iloc[begin:end], factors.iloc[begin:end], settings)
        rolling.append(
            {
                "date": str(returns.index[end - 1]),
                "alpha": calculated["annualised_alpha"],
                "lower": calculated["annualised_confidence_interval"][0]
                if calculated["annualised_confidence_interval"]
                else None,
                "upper": calculated["annualised_confidence_interval"][1]
                if calculated["annualised_confidence_interval"]
                else None,
                "p_value": calculated["p_value"],
                "state": calculated["state"],
            }
        )
    total_excess = None
    if benchmark is not None:
        if not returns.index.equals(benchmark.index):
            raise ValueError("Benchmark dates must align exactly")
        if (
            len(returns) > 0
            and np.isfinite(returns).all()
            and np.isfinite(benchmark).all()
            and (returns > -1).all()
            and (benchmark > -1).all()
        ):
            total_excess = finite(np.prod(1 + returns) - np.prod(1 + benchmark))
    return {
        **result,
        "raw_cumulative_excess_return": total_excess,
        "rolling": rolling,
        "warnings": [
            "A positive excess return or regression intercept does not establish a persistent investment edge.",
            "HAC adjusts covariance estimates, not survivorship bias, omitted factors or data-snooping. Multiple tests and selected parameters require separate review.",
        ],
    }
