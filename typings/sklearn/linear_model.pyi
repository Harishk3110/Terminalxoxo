import numpy as np
from numpy.typing import NDArray

from .base import BaseEstimator

class LinearRegression(BaseEstimator):
    coef_: NDArray[np.float64]
    def __init__(self) -> None: ...

class LogisticRegression(BaseEstimator):
    coef_: NDArray[np.float64]
    def __init__(
        self,
        *,
        C: float = 1.0,
        max_iter: int = 100,
        random_state: int | None = None,
    ) -> None: ...

class Ridge(BaseEstimator):
    coef_: NDArray[np.float64]
    def __init__(self, alpha: float = 1.0) -> None: ...

class Lasso(BaseEstimator):
    coef_: NDArray[np.float64]
    def __init__(
        self,
        alpha: float = 1.0,
        *,
        max_iter: int = 1000,
        random_state: int | None = None,
    ) -> None: ...

class ElasticNet(BaseEstimator):
    coef_: NDArray[np.float64]
    def __init__(
        self,
        alpha: float = 1.0,
        *,
        max_iter: int = 1000,
        random_state: int | None = None,
    ) -> None: ...
