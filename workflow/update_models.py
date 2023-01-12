import requests
import os
from conf import conf
from loguru import logger
import time

if __name__ == "__main__":
    time.sleep(conf.sleep)
    response = requests.get(f"{conf.base_hf_url}/update_models", headers={"token": os.getenv("API_TOKEN")})
    logger.info(response.json())
