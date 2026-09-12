import numpy as np
from numpy.typing import NDArray

from .base import BaseEstimator

class StandardScaler(BaseEstimator):
    mean_: NDArray[np.float64] | None
    scale_: NDArray[np.float64] | None
    def __init__(
        self,
        *,
        copy: bool = True,
        with_mean: bool = True,
        with_std: bool = True,
    ) -> None: ...
