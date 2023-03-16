from __future__ import annotations

from logger import get_configured_logger
from datetime import date, timedelta, datetime
from time import sleep
from typing import List, Union
import os

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

log = get_configured_logger(__name__)

URLS_CSV = "data/article_urls.csv"


class DailyMailScraper:

    def __init__(self, chrome_args: List[str]):
        self.chrome_options = Options()
        for arg in chrome_args:
            self.chrome_options.add_argument(arg)

        self.url_base = "https://www.dailymail.co.uk/home/sitemaparchive/"
        self.extension = ".html"
        self.article_cont_xpath = '//*[@id="content"]/div/div[1]/ul[2]'
        self.timeout = 3
        self.sleep_time = 1

        self.max_cons_errors = 3
        self.cons_errors = 0

    def __enter__(self) -> DailyMailScraper:
        self.driver = webdriver.Chrome(options=self.chrome_options)
        log.info("DailyMailScraper initialised")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.driver.quit()
        log.info("DailyMailScraper safely closed")

    def run(self, year: int) -> None:
        self.get_all_article_urls_in_year(year)

    def get_element_by_xpath(self, xpath) -> List:
        """Waits for element to appear or timeout to be reached before retrieving element"""
        try:
            WebDriverWait(self.driver, self.timeout).until(EC.presence_of_element_located((By.XPATH, xpath)))
            return self.driver.find_elements(By.XPATH, xpath)
        except TimeoutException:
            log.warning(f"Timeout error: could not retrieve xpath {xpath}")

    def get_archive_url(self, selected_date: date) -> str:
        """Retrieves the url listing all articles for a given date"""
        str_date = selected_date.strftime("%Y%m%d")
        return self.url_base + "day_" + str_date + self.extension

    @staticmethod
    def get_required_dates(year: int, start_date: date) -> List[date]:
        """Returns a list of every un-scraped date in the selected year.
        If current year, returns up to present day"""
        year_start = date(year, 1, 1)
        start_date = year_start if start_date is None else start_date

        today = date.today()
        year_end = date(year, 12, 31)
        end_date = min([today, year_end])

        all_dates = [(start_date + timedelta(days=x)) for x in
                     range((end_date - start_date).days + 1)]
        return all_dates

    def get_all_article_urls_on_date(self, selected_date: date) -> List[str]:
        """Retrieve all article urls for a given archive date"""
        sleep(self.sleep_time)
        archive_url = self.get_archive_url(selected_date)
        log_date = selected_date.strftime("%d-%m-%Y")

        try:
            self.driver.get(archive_url)
            article_container = self.get_element_by_xpath(self.article_cont_xpath)[0]
            all_urls = [a.get_attribute("href") for a in article_container.find_elements(By.TAG_NAME, "a")]
            self.cons_errors = 0
            log.info(f"{log_date} - success")
        except:
            self.cons_errors += 1
            all_urls = []
            log.warning(f"{log_date} - empty error")

        if self.cons_errors >= self.max_cons_errors:
            raise ConnectionRefusedError(f"{self.cons_errors} consecutive error limit reached. Ending process.")

        return all_urls

    def get_all_article_urls_in_year(self, year: int) -> None:
        """Retrieve all urls and dates for the given year"""
        existing_urls, last_date = self.load_existing_urls(path=URLS_CSV, year=year)
        year_dates = self.get_required_dates(year=year, start_date=last_date)[:5]
        archive_urls = {d.strftime("%d-%m-%Y"): self.get_all_article_urls_on_date(d) for d in year_dates}
        df = pd.DataFrame.from_dict(archive_urls, orient="index").T
        df.to_csv(URLS_CSV, index=False)
        log.info(f"All urls collected for {year}")

    @staticmethod
    def load_existing_urls(path: str, year: int) -> (pd.DataFrame, Union[str, None]):
        """If year has already been partially scraped, load csv and set start date as
        the day after the last day scraped."""
        if os.path.exists(path):
            df = pd.read_csv(URLS_CSV)
            last_date = datetime.strptime(max(df.columns), "%d-%m-%Y").date()
            start_date = last_date + timedelta(days=1)
            log.info(f"Existing urls found. Resuming from {start_date}")
            return df, start_date
        else:
            log.info(f"No existing data for selected {year}. Beginning from 1st January")
            return pd.DataFrame(), None


if __name__ == "__main__":
    with DailyMailScraper(chrome_args=['--disable-dev-shm-usage', '--no-sandbox']) as dms:
        dms.run(2023)
