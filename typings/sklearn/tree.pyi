import numpy as np
from numpy.typing import NDArray

from .base import BaseEstimator

class DecisionTreeRegressor(BaseEstimator):
    feature_importances_: NDArray[np.float64]
    def __init__(
        self,
        *,
        max_depth: int | None = None,
        min_samples_leaf: int = 1,
        random_state: int | None = None,
    ) -> None: ...
