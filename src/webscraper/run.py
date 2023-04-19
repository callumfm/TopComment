import argparse
import asyncio
from typing import List
from datetime import datetime, date
import pandas as pd

from webscraper.dates import get_dates
import utils.logger as logs
from webscraper.scraper import DailyMailScraper

log = logs.CustomLogger(__name__)


def parse_args(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", type=str, required=True)
    parser.add_argument("--end-date", type=str, required=True)

    return parser.parse_args(argv)


def get_parsed_dates(argv: List = None):
    args = parse_args(argv)
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").date()
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date()
    log.info(f"Date range: {start_date} - {end_date}")
    dates = get_dates(start_date=start_date, end_date=end_date)

    return dates


async def get_top_articles(dates: List[date]) -> pd.DataFrame:
    """Get best daily articles for data range"""
    async with DailyMailScraper() as dms:
        top_daily_articles = await asyncio.gather(
            *[dms.process_date(date_) for date_ in dates]
        )
    return pd.concat(top_daily_articles)


if __name__ == "__main__":
    log.info("Starting new pipeline run")
    dates = get_parsed_dates()
    top_articles = asyncio.run(get_top_articles(dates))
    print(top_articles)
