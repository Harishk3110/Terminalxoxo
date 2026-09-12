from typing import Self

import numpy as np
from numpy.typing import ArrayLike, NDArray

from .base import BaseEstimator

class Pipeline(BaseEstimator):
    steps: list[tuple[str, BaseEstimator]]
    def fit(self, X: ArrayLike, y: ArrayLike | None = None) -> Self: ...
    def predict(
        self,
        X: ArrayLike,
    ) -> NDArray[np.float64] | NDArray[np.int64] | NDArray[np.int32]: ...
    def predict_proba(self, X: ArrayLike) -> NDArray[np.float64]: ...

def make_pipeline(*steps: BaseEstimator) -> Pipeline: ...
