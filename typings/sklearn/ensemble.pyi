import numpy as np
from numpy.typing import NDArray

from .base import BaseEstimator

class RandomForestRegressor(BaseEstimator):
    feature_importances_: NDArray[np.float64]
    def __init__(
        self,
        n_estimators: int = 100,
        *,
        max_depth: int | None = None,
        min_samples_leaf: int = 1,
        n_jobs: int | None = None,
        random_state: int | None = None,
    ) -> None: ...

class GradientBoostingRegressor(BaseEstimator):
    feature_importances_: NDArray[np.float64]
    def __init__(
        self,
        *,
        n_estimators: int = 100,
        max_depth: int = 3,
        random_state: int | None = None,
    ) -> None: ...

class VotingRegressor(BaseEstimator):
    def __init__(
        self,
        estimators: list[tuple[str, BaseEstimator]],
        *,
        n_jobs: int | None = None,
    ) -> None: ...
