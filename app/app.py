import pickle
import zipfile

import pandas as pd
import gradio as gr
import plotly.express as px
import requests
from loguru import logger

from conf import conf
from utils import get_data
import os


class ModelStore:
    def __init__(self, username, repo_name, token):
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.github_url = f"https://api.github.com/repos/{username}/{repo_name}/actions/artifacts"
        self.models = {}

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
        response = requests.get(self.github_url, headers=self.headers)
        artifact_data = response.json()
        logger.info(artifact_data)
        return artifact_data["artifacts"][0]

    def load_models(self):
        self.__download_models()
        for package in conf.packages:
            with open(f"/tmp/models/{package}.pkl", "rb") as pkl:
                logger.info(f"loading model {package}.pkl")
                self.models.update({package: pickle.load(pkl)})
        return self

    def get(self, package):
        if self.models:
            return self.models.get(package)


class App:
    def __init__(self):
        token = os.getenv("GITHUB_TOKEN")
        # logger.debug(token)
        self.model_store = ModelStore(conf.username, conf.repo_name, token).load_models()

    def package_forecast(self, package):
        model = self.model_store.get(package)
        df = get_data(package)
        forecasts = model.predict(conf.forecast_days)
        df["date"] = pd.to_datetime(df["date"], infer_datetime_format=True)

        forecast_duration = pd.date_range(df["date"].max(), periods=conf.forecast_days, freq='D')
        fig = px.line(df, x=df["date"], y="downloads", title="Forecast")
        fig.add_scatter(x=forecast_duration, y=forecasts, mode="lines", name="Forecast", line=dict(width=2, color="green"))
        fig.update_layout(
            title="Forecast for " + package,
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

if __name__ == "__main__":
    app.launch()
