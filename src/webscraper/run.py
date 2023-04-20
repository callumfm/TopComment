import argparse
import asyncio
from typing import List, Tuple
from datetime import datetime, date
import pandas as pd

from configs.config import load_config
from webscraper.dates import get_dates
import utils.logger as logs
from webscraper.scraper import DailyMailScraper

log = logs.CustomLogger(__name__)


def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", type=str, required=True)
    parser.add_argument("--end-date", type=str, required=True)
    parser.add_argument("--n-top-comments", type=int, default=1, required=True)

    return parser.parse_args(argv)


def process_args(argv: List = None) -> Tuple[List[date], int]:
    args = parse_args(argv)
    start_date = datetime.strptime(args.start_date, "%d/%m/%Y").date()
    end_date = datetime.strptime(args.end_date, "%d/%m/%Y").date()
    log.info(f"Date range: {start_date} - {end_date}")
    dates = get_dates(start_date=start_date, end_date=end_date)

    return dates, args.n_top_comments


async def get_top_articles(dates: List[date], scraper_config: dict) -> pd.DataFrame:
    """Get best daily articles for data range"""
    async with DailyMailScraper(**scraper_config) as dms:
        top_daily_articles = await asyncio.gather(
            *[dms.process_date(date_) for date_ in dates]
        )

    return pd.concat(top_daily_articles)


if __name__ == "__main__":
    log.info("Starting new pipeline run")
    dates, n_top = process_args()
    scraper_config = load_config("webscraper/scraper_config.yaml")
    scraper_config["n_top_comments"] = n_top
    top_articles = asyncio.run(get_top_articles(dates=dates, scraper_config=scraper_config))
    print(top_articles)
