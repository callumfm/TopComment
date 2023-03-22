from datetime import date
from typing import List, Dict

import pandas as pd

from dates import get_week_num, get_dates_article_urls, get_dates
from logger import get_configured_logger
from scraper import SeleniumScraper
from config import START_DATE, END_DATE, LOG_N_ITER, GET_WORST, URLS_CSV

log = get_configured_logger(__name__)


def create_df_output(
    comments: List[Dict], url: str, date_: date, article_num: int
) -> pd.DataFrame:
    df = pd.DataFrame(comments).drop_duplicates()
    df["article_num"] = article_num
    df["url"] = url
    df["date"] = date_
    df = df.set_index("date")
    return df


def main():
    dates = get_dates(start_date=START_DATE, end_date=END_DATE)
    top_weekly_articles = []

    with SeleniumScraper() as ss:
        article_of_the_week = None
        best_upvotes = 0
        current_week_num = get_week_num(dates[0])

        for date_ in dates:
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
                iteration = f"{i + 1}/{n_articles}"
                log_prefix = f"Week {week_num} | {date_} | {iteration} articles"

                if i+1 % LOG_N_ITER == 0:
                    log.info(log_prefix)

                ss.driver.get(url)
                best_comments = ss.get_button_comments(comment_type="Best rated")

                if not best_comments:
                    continue

                # If new best article found, get worst comments as well and store
                # Will contain duplicates to be removed later
                top_comment_upvotes = best_comments[0]["rating-button-up"]

                if top_comment_upvotes > best_upvotes:
                    log.info(
                        f"{log_prefix} - New top comment found with {top_comment_upvotes} upvotes - {url}"
                    )
                    best_upvotes = top_comment_upvotes

                    worst_comments = []
                    if GET_WORST:
                        worst_comments = ss.get_button_comments(
                            comment_type="Worst rated"
                        )

                    article_of_the_week = create_df_output(
                        comments=best_comments + worst_comments,
                        url=url,
                        date_=date_,
                        article_num=i,
                    )

    pd.concat(top_weekly_articles).to_csv(URLS_CSV)


if __name__ == "__main__":
    main()
