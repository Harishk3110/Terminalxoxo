"""The pinned NumPy OLS boundary retains Bartlett HAC covariance and t inference."""

import numpy as np
import pytest
import statsmodels
import statsmodels.api as sm
from scipy.stats import t


@pytest.mark.parametrize("lags", [0, 1, 5, 12])
def test_numpy_hac_result_matches_independent_matrix_calculation(lags: int) -> None:
    assert statsmodels.__version__ == "0.15.0"
    rng = np.random.default_rng(710)
    factors = rng.normal(0, 0.02, size=(120, 2))
    design = sm.add_constant(factors, has_constant="add")
    assert design.dtype == np.float64
    assert design.shape == (120, 3)
    np.testing.assert_array_equal(design[:, 0], np.ones(120))
    np.testing.assert_array_equal(design[:, 1:], factors)
    returns = 0.001 + factors @ np.array([1.2, -0.3]) + rng.normal(0, 0.004, 120)
    fit = sm.OLS(returns, design, missing="raise").fit(
        cov_type="HAC", cov_kwds={"maxlags": lags, "use_correction": True}, use_t=True
    )
    coefficients = np.linalg.lstsq(design, returns, rcond=None)[0]
    residuals = returns - design @ coefficients
    scores = design * residuals[:, None]
    meat = scores.T @ scores
    for lag in range(1, lags + 1):
        cross = scores[lag:].T @ scores[:-lag]
        meat += (1 - lag / (lags + 1)) * (cross + cross.T)
    bread = np.linalg.inv(design.T @ design)
    degrees = len(returns) - design.shape[1]
    covariance = len(returns) / degrees * (bread @ meat @ bread)
    errors = np.sqrt(np.diag(covariance))
    statistics = coefficients / errors
    intervals = np.column_stack(
        (
            coefficients - t.ppf(0.975, degrees) * errors,
            coefficients + t.ppf(0.975, degrees) * errors,
        )
    )
    for actual, expected in (
        (fit.params, coefficients),
        (fit.bse, errors),
        (fit.tvalues, statistics),
        (fit.pvalues, 2 * t.sf(np.abs(statistics), degrees)),
        (fit.conf_int(alpha=0.05), intervals),
    ):
        assert isinstance(actual, np.ndarray)
        assert actual.dtype == np.float64
        assert actual.shape == expected.shape
        np.testing.assert_allclose(actual, expected, rtol=1e-12, atol=1e-14)
    assert np.isfinite(fit.rsquared) and np.isfinite(fit.rsquared_adj)
