import pandas as pd

from .. import DataBase

class PandasData(DataBase):
    def __init__(self, *, dataname: pd.DataFrame) -> None: ...
