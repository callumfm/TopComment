from datetime import date
from typing import List, Dict

import pandas as pd

from utils.dates import get_week_num, get_dates_article_urls, get_dates
import utils.logger as logs
from web_scraper.scraper import SeleniumScraper
from config import START_DATE, END_DATE, LOG_N_ITER, URLS_CSV

log = logs.CustomLogger(__name__)


def create_df_output(
    comments: List[Dict], url: str, date_: date, article_num: int
) -> pd.DataFrame:
    df = pd.DataFrame(comments).drop_duplicates()
    df["article_num"] = article_num
    df["url"] = url
    df["date"] = date_
    df = df.set_index("date")
    return df


def process_article(ss: SeleniumScraper, url: str, best_upvotes: int, date_: date, i: int):
    """Process single article"""
    ss.driver.get(url)
    best_comments = ss.get_button_comments(comment_type="Best rated")

    if not best_comments:
        return

    top_comment_upvotes = best_comments[0]["rating-button-up"]

    if top_comment_upvotes > best_upvotes:
        log.info(
            "New top comment found with {top_comment_upvotes} upvotes - {url}",
            prefix=logs.PREFIX
        )
        best_upvotes = top_comment_upvotes

        article_of_the_week = create_df_output(
            comments=best_comments,
            url=url,
            date_=date_,
            article_num=i,
        )
        return best_upvotes, article_of_the_week


def process_date(
        ss: SeleniumScraper,
        date_: date,
        current_week_num: int,
        best_upvotes: int,
        top_weekly_articles: List,
        article_of_the_week: pd.DataFrame
):
    """Process all articles on date"""
    article_urls = get_dates_article_urls(date_)
    n_articles = len(article_urls)
    week_num = get_week_num(date_)

    # If new week, store best article and reset counters
    if week_num != current_week_num:
        log.info(f"Week {week_num} scan complete, storing best article")
        top_weekly_articles.append(article_of_the_week)
        best_upvotes = 0
        current_week_num = week_num

    # For each article on date, check number of best rated comment upvotes
    for i, url in enumerate(article_urls):
        logs.PREFIX = f"Week {week_num} | {date_} | {i + 1}/{n_articles} articles"

        if i + 1 % LOG_N_ITER == 0:
            log.info(logs.PREFIX)

        res = process_article(ss, url, best_upvotes, date_, i)

        if res is None:
            continue

        best_upvotes, article_of_the_week = res

    return current_week_num, best_upvotes, article_of_the_week, top_weekly_articles


def main():
    dates = get_dates(start_date=START_DATE, end_date=END_DATE)
    top_weekly_articles = []
    article_of_the_week = None
    best_upvotes = 0
    current_week_num = get_week_num(dates[0])

    with SeleniumScraper() as ss:
        for date_ in dates:
            current_week_num, best_upvotes, article_of_the_week, top_weekly_articles = process_date(
                ss, date_, current_week_num, best_upvotes, top_weekly_articles, article_of_the_week
            )

    pd.concat(top_weekly_articles).to_csv(URLS_CSV)


if __name__ == "__main__":
    main()
