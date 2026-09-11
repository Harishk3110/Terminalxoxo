from typing import Literal

import numpy as np
import pytest
from app.monte_carlo import MonteCarloSettings, monte_carlo


@pytest.mark.parametrize("method", ["BOOTSTRAP", "BLOCK_BOOTSTRAP", "NORMAL", "SHUFFLE"])
def test_seeded_paths_probabilities_and_fan(
    method: Literal["BOOTSTRAP", "BLOCK_BOOTSTRAP", "NORMAL", "SHUFFLE"],
) -> None:
    returns = np.random.default_rng(18).normal(0.0002, 0.01, 300)
    settings = MonteCarloSettings(method=method, paths=100, horizon=50)
    result = monte_carlo(returns, settings)
    assert result == monte_carlo(returns, settings)
    assert all(
        0 <= result["metrics"][key] <= 1
        for key in ("loss_probability", "drawdown_probability", "ruin_probability")
    )
    assert result["fan"][0]["p50"] == settings.capital
    assert all(row["p05"] <= row["p50"] <= row["p95"] for row in result["fan"])
    assert sum(row["count"] for row in result["terminal_distribution"]) == 100


def test_constant_returns_and_ineligible_history() -> None:
    data = monte_carlo([0.001] * 100, MonteCarloSettings(paths=100, horizon=10))
    assert data["metrics"]["median_return"] == pytest.approx(1.001**10 - 1)
    assert data["metrics"]["drawdown_probability"] == 0
    for values in ([0.01] * 59, [0.01] * 60 + [None], [-1] * 60):
        with pytest.raises(ValueError):
            monte_carlo(np.asarray(values, dtype=object), MonteCarloSettings())
