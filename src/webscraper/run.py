import argparse
import asyncio
import os
from datetime import date, datetime
from typing import List, Tuple

import pandas as pd

import src.utils.logger as logs
from src.configs.config import load_config
from src import DATA_DIR
from src.webscraper.dates import get_dates
from src.webscraper.scraper import DailyMailScraper

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


def save_checkpoint(top_articles: List[pd.DataFrame], date_: date):
    if not os.path.exists(DATA_DIR):
        os.mkdir(DATA_DIR)

    for file in os.listdir(DATA_DIR):
        if file.startswith("CHECKPOINT_"):
            os.remove(os.path.join(DATA_DIR, file))

    date_str = datetime.strftime(date_, "%d%m%Y")
    filename = f"CHECKPOINT_{date_str}.csv"
    filepath = os.path.join(DATA_DIR, filename)

    df = pd.concat(top_articles)
    df.to_csv(filepath)
    log.info("Day succesfully scraped - Saving new checkpoint", prefix=logs.PREFIX)


def resume_checkpoint():
    checkpoints = os.listdir(DATA_DIR)

    if not checkpoints:
        return []

    log.info("Previous checkpoint found - Resuming")
    file = os.path.join(DATA_DIR, checkpoints[0])
    df = pd.read_csv(file)
    return df


def save_output(top_articles: List[pd.DataFrame], date_range: List[date]) -> None:
    start_date = datetime.strftime(date_range[0], "%d%m%Y")
    end_date = datetime.strftime(date_range[1], "%d%m%Y")
    filename = f"OUTPUT_{start_date}_{end_date}.csv"
    filepath = os.path.join(DATA_DIR, filename)

    df = pd.concat(top_articles)
    df.to_csv(filepath)
    log.info("Run complete - Saving output")


async def get_top_articles(
    dates: List[date], scraper_config: dict
) -> List[pd.DataFrame]:
    """Get best daily articles for data range"""
    top_articles = []
    async with DailyMailScraper(**scraper_config) as dms:
        for date_ in dates:
            top_date_article = await dms.process_date(date_)
            top_articles.append(top_date_article)
            save_checkpoint(top_articles, date_)

    return top_articles


if __name__ == "__main__":
    log.info("Starting new pipeline run")
    dates, n_top = process_args()
    scraper_config = load_config("webscraper/scraper_config.yaml")
    scraper_config["n_top_comments"] = n_top
    top_articles = asyncio.run(
        get_top_articles(dates=dates, scraper_config=scraper_config)
    )
    save_output(top_articles=top_articles, date_range=dates)
