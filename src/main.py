import argparse
from datetime import datetime
from typing import List

import numpy as np

import src.utils.logger as logs
from src.cloud_sdk.gcp_client import GCPClient
from src.configs.config import load_config
from src.webscraper.dates import get_dates

log = logs.CustomLogger(__name__)

"""
1 VM instance ~= £0.80 per day
1 article ~= 5 seconds compute time
1 day ~= 1,750 articles ~= 0.1 days compute time

3 months articles ~= 9 days compute time (1 instance, £7.20)
                  ~= 1 day compute time (9 instances, £7.20)
"""


def parse_args(argv=None) -> argparse.Namespace:
    """Arguments for root pipeline call"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", type=str, required=True)
    parser.add_argument("--end-date", type=str, required=True)
    parser.add_argument("--n-top-comments", type=int, default=1, required=False)

    return parser.parse_args(argv)


def create_instance_scripts(
    n_instances: int, start_date: str, end_date: str, n_top_comments: int
) -> List[str]:
    """Create Python scraper script for each instance to run"""
    start_date = datetime.strptime(start_date, "%d/%m/%Y").date()
    end_date = datetime.strptime(end_date, "%d/%m/%Y").date()
    dates = get_dates(start_date=start_date, end_date=end_date)
    date_groups = np.array_split(dates, n_instances)

    scripts = []
    for dates_seg in date_groups:
        start_date = datetime.strftime(dates_seg[0], "%d/%m/%Y")
        end_date = datetime.strftime(dates_seg[-1], "%d/%m/%Y")
        script = (
            "export PYTHONPATH=/usr/local/TopComment/src\n"
            + "cd /usr/local/TopComment/src\n"
            + f"python3 webscraper/run.py --start-date {start_date} --end-date {end_date} --n-top-comments {n_top_comments}"
        )
        scripts.append(script)

    return scripts


def full_pipeline(argv: List = None) -> None:
    """
    Main pipeline runner. Creates instances on GCP and executes scraper
    script for unique date range.
    """
    args = parse_args(argv)
    config = load_config("cloud_sdk/cloud_config.yaml")
    n_instances = config["vm_instances"]["num_instances"]

    log.info("Starting new pipeline run")
    log.info(f"Date range: {args.start_date} - {args.end_date}")
    log.info(f"Number of instances: {n_instances}")

    scripts = create_instance_scripts(
        n_instances=n_instances,
        start_date=args.start_date,
        end_date=args.end_date,
        n_top_comments=args.n_top_comments,
    )
    GCPClient(config).run(num_instances=n_instances, scripts=scripts)


if __name__ == "__main__":
    full_pipeline()
