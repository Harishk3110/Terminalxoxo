"""NumPy regression surface consumed by alpha_statistics; verified against 0.15.0."""

from typing import Literal, Protocol

import numpy as np
from numpy.typing import NDArray

type _FloatArray = NDArray[np.float64]

class _ArrayRegressionResult(Protocol):
    @property
    def params(self) -> _FloatArray: ...
    @property
    def bse(self) -> _FloatArray: ...
    @property
    def tvalues(self) -> _FloatArray: ...
    @property
    def pvalues(self) -> _FloatArray: ...
    @property
    def rsquared(self) -> float | np.float64: ...
    @property
    def rsquared_adj(self) -> float | np.float64: ...
    def conf_int(self, alpha: float = 0.05) -> _FloatArray: ...

def add_constant(
    data: _FloatArray,
    prepend: bool = True,
    has_constant: Literal["raise", "add", "skip"] = "skip",
) -> _FloatArray: ...

class OLS:
    def __init__(
        self,
        endog: _FloatArray,
        exog: _FloatArray | None = None,
        missing: Literal["none", "drop", "raise"] = "none",
        hasconst: bool | None = None,
        **kwargs: object,
    ) -> None: ...
    def fit(
        self,
        method: Literal["pinv", "qr"] = "pinv",
        cov_type: str = "nonrobust",
        cov_kwds: dict[str, int | bool] | None = None,
        use_t: bool | None = None,
        **kwargs: object,
    ) -> _ArrayRegressionResult: ...
