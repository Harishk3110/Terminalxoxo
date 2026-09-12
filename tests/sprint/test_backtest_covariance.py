"""Invalid covariance inputs cannot masquerade as valid allocation weights."""

import numpy as np
import pytest
from app.backtest_engine import risk_parity
from numpy.typing import NDArray


@pytest.mark.parametrize(
    "covariance",
    [
        np.array([[np.nan]]),
        np.array([[np.inf]]),
        np.array([[-0.01]]),
        np.empty((0, 0)),
        np.array([0.01, 0.04]),
        np.array([[0.01, 0.0], [0.02, 0.04]]),
        np.array([[0.01, 0.02]]),
        np.array([[0.01, 0.02], [0.02, 0.01]]),
    ],
    ids=[
        "single-nan",
        "single-infinite",
        "single-negative",
        "empty",
        "vector",
        "asymmetric",
        "rectangular",
        "indefinite",
    ],
)
def test_risk_parity_rejects_invalid_covariance(covariance: NDArray[np.float64]) -> None:
    with pytest.raises(ValueError):
        risk_parity(covariance)


def test_positive_single_asset_covariance_has_exact_unit_weight() -> None:
    weights = risk_parity(np.array([[0.04]]))
    assert weights.dtype == np.float64 and weights.shape == (1,)
    np.testing.assert_array_equal(weights, np.array([1.0]))
