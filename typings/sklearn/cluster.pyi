from typing import Literal

from .base import BaseEstimator

class KMeans(BaseEstimator):
    def __init__(
        self,
        n_clusters: int = 8,
        *,
        n_init: int | Literal["auto"] = "auto",
        random_state: int | None = None,
    ) -> None: ...
