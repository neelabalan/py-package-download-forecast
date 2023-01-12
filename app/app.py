import os
import pickle
import zipfile
from datetime import datetime
from typing import Union

import gradio as gr
import pandas as pd
import plotly.express as px
import requests
import uvicorn
from fastapi import FastAPI
from fastapi import Header
from loguru import logger

from conf import conf
from utils import get_data

fast_api = FastAPI()


MODELS = {}
TITLE = ""


def convert_to_apt_datetime_string(datestr):
    return datetime.strftime(datetime.strptime(datestr, "%Y-%m-%dT%H:%M:%SZ"), "%Y-%m-%d")


class ModelStore:
    global MODELS

    def __init__(self, username, repo_name, token):
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.github_url = f"https://api.github.com/repos/{username}/{repo_name}/actions/artifacts"

    def __download_models(self):
        recent_artifact = self.__get_latest_artifact_data()
        recent_artifact_download_url = recent_artifact["archive_download_url"]
        response = requests.get(recent_artifact_download_url, headers=self.headers, stream=True)

        with open("/tmp/models.zip", "wb") as f:
            for chunk in response.iter_content(chunk_size=512):
                if chunk:
                    # filter out keep-alive new chunks
                    f.write(chunk)

        z = zipfile.ZipFile("/tmp/models.zip")
        z.extractall("/tmp/models/")

    def __get_latest_artifact_data(self):
        global TITLE
        response = requests.get(self.github_url, headers=self.headers)
        artifact_data = response.json()
        logger.info(artifact_data)
        # update title with last updated date
        last_updated_at = artifact_data["artifacts"][0]["updated_at"]
        TITLE = f"Last model updated on {convert_to_apt_datetime_string(last_updated_at)}<br><br>Forecast for "
        return artifact_data["artifacts"][0]

    def load_models(self):
        self.__download_models()
        for package in conf.packages:
            with open(f"/tmp/models/{package}.pkl", "rb") as pkl:
                logger.info(f"loading model {package}.pkl")
                MODELS.update({package: pickle.load(pkl)})
        return self

    def get(self, package):
        if MODELS:
            return MODELS.get(package)


class App:
    def __init__(self):
        token = os.getenv("GITHUB_TOKEN")
        # logger.debug(token)
        self.model_store = ModelStore(conf.username, conf.repo_name, token).load_models()

    def package_forecast(self, package):
        global TITLE
        model = self.model_store.get(package)
        df = get_data(package)
        forecasts = model.predict(conf.forecast_days)
        df["date"] = pd.to_datetime(df["date"], infer_datetime_format=True)

        forecast_duration = pd.date_range(df["date"].max(), periods=conf.forecast_days, freq="D")
        fig = px.line(df, x=df["date"], y="downloads", title="Forecast")
        fig.add_scatter(
            x=forecast_duration, y=forecasts, mode="lines", name="Forecast", line=dict(width=2, color="green")
        )
        fig.update_layout(
            title=TITLE + package,
            xaxis_title="Date",
            yaxis_title="Downloads",
        )
        return fig


inputs = [
    gr.Dropdown(conf.packages, label="Package"),
]
outputs = gr.Plot()

app = gr.Interface(
    fn=App().package_forecast,
    inputs=inputs,
    outputs=outputs,
    examples=[conf.packages],
    cache_examples=True,
)


@fast_api.get("/update_models")
def update_to_lastest_models(token: Union[str, None] = Header(default=None)):
    global MODELS
    if os.getenv("GITHUB_TOKEN") == token:
        model_store = ModelStore(conf.username, conf.repo_name, token).load_models()
        logger.info("models updated successfully")
        return {"message": "models updated successfully"}
    else:
        return {"message": "No or wrong token passed"}


fast_api = gr.mount_gradio_app(fast_api, app, path="")


if __name__ == "__main__":
    uvicorn.run(fast_api, host="0.0.0.0", port=7860)
