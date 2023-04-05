from datetime import date, timedelta
from typing import List

import requests
from bs4 import BeautifulSoup
from dateutil.relativedelta import relativedelta


def get_dates(start_date: date = None, end_date: date = None) -> List[date]:
    if not end_date:
        end_date = date.today()

    if not start_date:
        start_date = end_date + relativedelta(months=-6)

    all_dates = [
        (start_date + timedelta(days=x))
        for x in range((end_date - start_date).days + 1)
    ]
    return all_dates


def get_dates_article_urls(d: date) -> List[str]:
    str_date = d.strftime("%Y%m%d")
    archive_url = f"https://www.dailymail.co.uk/home/sitemaparchive/day_{str_date}.html"
    res = requests.get(archive_url)
    soup = BeautifulSoup(res.content, "html.parser")

    container = soup.find_all("div", {"class": "alpha debate sitemap"})

    if not container:
        raise ValueError("Container not found")

    links = container[0].find_all("a")
    base_url = "https://www.dailymail.co.uk"
    article_urls = [base_url + link.get("href") + "#comments" for link in links]
    return article_urls[3:]


def get_week_num(date_: date) -> int:
    return date_.isocalendar()[1]
