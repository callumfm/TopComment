import numpy as np

import utils.logger as logs
from cloud_sdk.gcp_client import MIGClient
from configs.webscraper.runner_config import START_DATE, END_DATE, URLS_CSV
from webscraper.dates import get_dates

log = logs.CustomLogger(__name__)


if __name__ == "__main__":
    log.info("Starting new pipeline run")
    log.info(f"Date range: {START_DATE} - {END_DATE}")

    dates = get_dates(start_date=START_DATE, end_date=END_DATE)
    dates_split = np.array_split(dates)

    mig_config = read_config("cloud_sdk/project_config.yaml")
    script = ""

    with MIGClient(**mig_config) as gcp_client:
        res = gcp_client.execute_script_on_all_instances(script)
        res.to_csv(URLS_CSV)
