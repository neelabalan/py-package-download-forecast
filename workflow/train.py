import os
import pickle
from typing import List
from typing import Tuple
from typing import Union

import numpy as np
import pandas as pd
import pmdarima as pm
from loguru import logger
from pmdarima.model_selection import train_test_split

from conf import conf
from utils import calc_rmse
from utils import forecast
from utils import get_data


def tune(y: Union[np.array, pd.Series]) -> Tuple[int, float]:
    """Get the best 'm' value"""
    rmse: List[Tuple(int, float)] = []
    for m in conf.m_values:
        prediction = train(y, m)
        actuals = y[len(prediction) :]
        rmse.append((m, calc_rmse(prediction, actuals)))
    return sorted(rmse, key=lambda tup: tup[1])[0]


def train(y: Union[np.array, pd.Series], m: int, train_size: int = 150) -> Union[np.array, pd.Series]:
    train, test = train_test_split(y, train_size=train_size)
    return forecast(train, m=m, steps=test.shape[0])


def run():
    """
    Collect data and dump the best model
    """
    os.makedirs("/tmp/models", exist_ok=True)
    for package in conf.packages:
        df = get_data(package)
        y = df["downloads"]
        best_m, best_rmse = tune(y)
        logger.info(f"best m {best_m}, best RMSE {best_rmse}")
        model = pm.auto_arima(y, seasonal=True, m=best_m)
        with open(f"/tmp/models/{package}.pkl", "wb") as pkl:
            pickle.dump(model, pkl)


if __name__ == "__main__":
    run()
