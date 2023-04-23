import argparse
from typing import List

import numpy as np

import utils.logger as logs
from cloud_sdk.gcp_client import GCPClient
from webscraper.dates import get_dates
from configs.config import load_config
from datetime import datetime

log = logs.CustomLogger(__name__)


def parse_args(argv=None) -> argparse.Namespace:
    """Arguments for root pipeline call"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", type=str, required=True)
    parser.add_argument("--end-date", type=str, required=True)
    parser.add_argument("--n-top-comments", type=int, default=1, required=False)
    parser.add_argument("--save-path", type=str, default="data/top_weekly.csv", required=False)

    return parser.parse_args(argv)


def create_instance_scripts(n_instances: int, start_date: str, end_date: str, n_top_comments: int) -> List[str]:
    """Create Python scraper script for each instance to run"""
    start_date = datetime.strptime(start_date, "%d/%m/%Y").date()
    end_date = datetime.strptime(end_date, "%d/%m/%Y").date()
    dates = get_dates(start_date=start_date, end_date=end_date)
    date_groups = np.array_split(dates, n_instances)
    scripts = [
        f"python -m webscraper/run.py --start-date {dg[0]} --end-date {dg[-1]} --n-top-comments {n_top_comments}"
        for dg in date_groups
    ]

    return scripts


def full_pipeline(argv: List = None) -> None:
    """
    Main pipeline runner. Creates instances on GCP and executes scraper
    script for unique date range.
    """
    args = parse_args(argv)
    config = load_config("cloud_sdk/cloud_config.yaml")
    n_instances = config["managed_instance_group"]["num_instances"]

    log.info("Starting new pipeline run")
    log.info(f"Date range: {args.start_date} - {args.end_date}")
    log.info(f"Number of instances: {n_instances}")

    # scripts = create_instance_scripts(
    #     n_instances=mig_config['num_instances'],
    #     start_date=args.start_date,
    #     end_date=args.end_date,
    #     n_top_comments=args.n_top_comments,
    # )

    script = "python -m webscraper/test_script.py"

    with GCPClient(config) as gcp_client:
        instances = gcp_client.get_instances()
        gcp_client.execute_script_in_instance(
            instance=instances[0],
            script=script,
        )


if __name__ == "__main__":
    full_pipeline()
