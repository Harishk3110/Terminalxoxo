from collections.abc import Iterator

import numpy as np
from numpy.typing import ArrayLike, NDArray

class TimeSeriesSplit:
    def __init__(
        self,
        n_splits: int = 5,
        *,
        max_train_size: int | None = None,
        test_size: int | None = None,
        gap: int = 0,
    ) -> None: ...
    def split(
        self,
        X: ArrayLike,
        y: ArrayLike | None = None,
        groups: ArrayLike | None = None,
    ) -> Iterator[tuple[NDArray[np.int64], NDArray[np.int64]]]: ...
