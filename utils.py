from typing import List
from typing import Union

import numpy as np
import pandas as pd
import pmdarima as pm
import pypistats

from conf import conf


def calc_rmse(forecast, actuals):
    return np.sqrt(np.mean((forecast - actuals) ** 2))


# def get_all_data() -> List[pd.DataFrame]:
#     data = {}
#     for package in conf.packages:
#         df = (
#             pypistats.overall(package, total=True, format="pandas")
#             .groupby("category")
#             .get_group("with_mirrors")
#             .sort_values("date")
#             .drop(["percent", "category"], axis=1)
#         )
#         df["date"] = pd.to_datetime(df["date"], infer_datetime_format=True)
#         data.update({package: df})
#     return data


def get_data(package) -> List[pd.DataFrame]:
    df = (
        pypistats.overall(package, total=True, format="pandas")
        .groupby("category")
        .get_group("with_mirrors")
        .sort_values("date")
        .drop(["percent", "category"], axis=1)
    )
    df["date"] = pd.to_datetime(df["date"], infer_datetime_format=True)
    return df


def forecast(y: Union[np.array, pd.Series], m: int, steps: int = 13):
    model = pm.auto_arima(y, seasonal=True, m=m)
    return model.predict(steps)
