from datetime import date
from time import sleep
from typing import List, Literal, Union, Dict

import pandas as pd
from selenium import webdriver
from selenium.common import StaleElementReferenceException
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from configs.webscraper.runner_config import SLEEP, TIMEOUT, N_TOP_COMMENTS, CHROME_ARGS, LOG_N_ITER
from utils import logger as logs
from webscraper.dates import get_dates_article_urls, get_week_num

log = logs.CustomLogger(__name__)


class DailyMailScraper:
    def __init__(
        self,
        chrome_args: List[str] = CHROME_ARGS,
        timeout: int = TIMEOUT,
        sleep_time: int = SLEEP,
    ):
        self.driver = None
        self.chrome_options = Options()
        for arg in chrome_args:
            self.chrome_options.add_argument(arg)
        self.timeout = timeout
        self.sleep_time = sleep_time

    async def __aenter__(self):
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.driver.maximize_window()
        log.info("Selenium scraper initialised", prefix=logs.PREFIX)
        await self.remove_base_pop_up()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        self.driver.quit()
        self.driver = None
        log.info("Selenium scraper safely closed", prefix=logs.PREFIX)
        if exc_type is not None:
            log.error(f"{exc_type}\n{exc_val}\n{exc_tb}", prefix=logs.PREFIX)

    def sleep_(self) -> None:
        sleep(self.sleep_time)

    def retry_(self) -> None:
        self.driver.refresh()
        self.remove_base_pop_up()

    async def remove_base_pop_up(self):
        """Load random article and remove 'Got it!' pop-up for session"""
        if self.driver is None:
            raise RuntimeError("webdriver instance not initialized")

        sample_url = (
            "https://www.dailymail.co.uk/wires/ap/article-11350651/"
            "Australia-reveal-economic-plan-deteriorating-outlook.html#html"
        )
        self.driver.get(sample_url)
        await self.click_dynamic_element(By.XPATH, "//button[text()='Got it']")

    async def get_dynamic_elements_by_custom(self, search_type: By, string: str):
        try:
            self.sleep_()
            condition = EC.presence_of_all_elements_located((search_type, string))
            wait = WebDriverWait(self.driver, self.timeout)
            element = wait.until(condition)
            return element
        except TimeoutException:
            log.warning(
                f"Timeout error: could not retrieve {search_type} {string}",
                prefix=logs.PREFIX,
            )

    async def click_dynamic_element(self, search_type: By, string: str) -> bool:
        try:
            self.sleep_()
            condition = EC.element_to_be_clickable((search_type, string))
            element = WebDriverWait(self.driver, self.timeout).until(condition)
            element.click()
            return True
        except ElementClickInterceptedException:
            log.debug(
                f"Pop up prevented {string} element from being clicked",
                prefix=logs.PREFIX,
            )
            await self.click_dynamic_element(search_type, string)
            return False
        except TimeoutException:
            log.debug(
                f"Timeout error: could not retrieve {search_type} {string}",
                prefix=logs.PREFIX,
            )
            return False

    async def get_button_comments(
        self,
        comment_type: Literal["Best rated", "Worst rated"],
        n_top: int = N_TOP_COMMENTS,
    ) -> List[Dict[str, Union[str, int]]]:
        """
        Retrieve comment body, upvotes and downvotes. Some articles have zero comments, hence just return empty list
        """
        comment_section = await self.click_dynamic_element(
            By.XPATH, f"//a[text()='{comment_type}']"
        )
        if not comment_section:
            return []

        button_cls = {
            "Best rated": "rating-button-up",
            "Worst rated": "rating-button-down",
        }
        button = button_cls[comment_type]

        if comment_type == "Best rated" and n_top > 1:
            await self.click_dynamic_element(By.XPATH, "//button[text()='Show More']")

        comment_divs = await self.get_dynamic_elements_by_custom(
            By.CSS_SELECTOR, '[class^="comment comment-"]'
        )
        return self.get_comment_content(comment_divs[:n_top], button=button)

    @staticmethod
    def get_comment_content(comment_divs, button) -> List[dict]:
        comment_content = []
        for i, comment in enumerate(comment_divs):
            comment_text = comment.find_element(By.CLASS_NAME, "comment-text").text
            votes = comment.find_element(By.CLASS_NAME, button).text
            data_dict = {"comment": comment_text, button: int(votes)}
            comment_content.append(data_dict)

        return comment_content

    @staticmethod
    def create_df_output(
        comments: List[Dict], url: str, date_: date, article_num: int
    ) -> pd.DataFrame:
        df = pd.DataFrame(comments).drop_duplicates()
        df["article_num"] = article_num
        df["url"] = url
        df["date"] = date_
        df = df.set_index("date")
        return df

    async def process_article(
        self,
        url: str,
        top_upvotes: int,
        top_article: pd.DataFrame,
        date_: date,
        i: int,
    ):
        """Process single article"""
        self.driver.get(url)

        try:
            top_comments = await self.get_button_comments(comment_type="Best rated")
        except StaleElementReferenceException:
            self.retry_()
            top_comments = await self.get_button_comments(comment_type="Best rated")

        if not top_comments:
            return top_upvotes, top_article

        top_comment_upvotes = top_comments[0]["rating-button-up"]

        if top_comment_upvotes > top_upvotes:
            log.info(
                f"New top comment found with {top_comment_upvotes} upvotes - {url}",
                prefix=logs.PREFIX,
            )
            top_upvotes = top_comment_upvotes

            top_article = self.create_df_output(
                comments=top_comments,
                url=url,
                date_=date_,
                article_num=i,
            )
            return top_upvotes, top_article

        return top_upvotes, top_article

    async def process_date(self, date_: date) -> pd.DataFrame:
        """Process all articles on date"""
        article_urls = get_dates_article_urls(date_)
        n_articles = len(article_urls)
        top_upvotes = 0
        top_article = None
        week_num = get_week_num(date_)

        # For each article on date, check number of top-rated comment upvotes
        for i, url in enumerate(article_urls):
            logs.PREFIX = f"Week {week_num} | {date_} | {i + 1}/{n_articles} articles"

            if (i + 1) % LOG_N_ITER == 0:
                log.info(logs.PREFIX)

            top_upvotes, top_article = await self.process_article(
                url, top_upvotes, top_article, date_, i
            )

        return top_article