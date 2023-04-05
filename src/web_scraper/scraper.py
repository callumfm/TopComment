from time import sleep
from typing import List, Literal, Union, Dict

from selenium import webdriver
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from config import SLEEP, TIMEOUT, N_TOP_COMMENTS, CHROME_ARGS
import utils.logger as logs

log = logs.CustomLogger(__name__)


class SeleniumScraper:
    def __init__(self, chrome_args: List[str] = CHROME_ARGS, timeout: int = TIMEOUT, sleep: int = SLEEP):
        self.chrome_options = Options()
        for arg in chrome_args:
            self.chrome_options.add_argument(arg)
        self.timeout = timeout
        self.sleep = sleep

    def __enter__(self):
        self.driver = webdriver.Chrome(options=self.chrome_options)
        self.driver.maximize_window()
        log.info("Selenium scraper initialised", prefix=logs.PREFIX)
        self.remove_base_pop_up()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.driver.quit()
        log.info("Selenium scraper safely closed", prefix=logs.PREFIX)

    def remove_base_pop_up(self):
        """Load random article and remove 'Got it!' pop-up for session"""
        self.driver.get(
            "https://www.dailymail.co.uk/wires/ap/article-11350651/"
            "Australia-reveal-economic-plan-deteriorating-outlook.html#html"
        )
        self.click_dynamic_element(By.XPATH, "//button[text()='Got it']")

    def get_dynamic_elements_by_custom(self, search_type: By, string: str):
        try:
            sleep(self.sleep)
            wait = WebDriverWait(self.driver, self.timeout)
            element = wait.until(
                EC.presence_of_all_elements_located((search_type, string))
            )
            return element
        except TimeoutException:
            log.warning(f"Timeout error: could not retrieve {search_type} {string}", prefix=logs.PREFIX)

    def click_dynamic_element(self, search_type: By, string: str) -> bool:
        try:
            sleep(self.sleep)
            WebDriverWait(self.driver, self.timeout).until(
                EC.element_to_be_clickable((search_type, string))
            ).click()
            return True
        except ElementClickInterceptedException:
            log.debug(f"Pop up prevented {string} element from being clicked", prefix=logs.PREFIX)
            self.click_dynamic_element(search_type, string)
            return False
        except TimeoutException:
            log.debug(f"Timeout error: could not retrieve {search_type} {string}", prefix=logs.PREFIX)
            return False

    def get_button_comments(
        self,
        comment_type: Literal["Best rated", "Worst rated"],
        n_top: int = N_TOP_COMMENTS,
    ) -> List[Dict[str, Union[str, int]]]:
        """
        Retrieve comment body, upvotes and downvotes. Some articles have zero comments, hence just return empty list
        """
        if not self.click_dynamic_element(By.XPATH, f"//a[text()='{comment_type}']"):
            return []

        button_cls = {
            "Best rated": "rating-button-up",
            "Worst rated": "rating-button-down",
        }
        button = button_cls[comment_type]

        if comment_type == "Best rated" and n_top > 1:
            self.click_dynamic_element(By.XPATH, "//button[text()='Show More']")

        comment_divs = self.get_dynamic_elements_by_custom(
            By.CSS_SELECTOR, '[class^="comment comment-"]'
        )[:n_top]

        comment_content = []
        for i, comment in enumerate(comment_divs):
            comment_text = comment.find_element(By.CLASS_NAME, "comment-text").text
            votes = comment.find_element(By.CLASS_NAME, button).text
            data_dict = {"comment": comment_text, button: int(votes)}
            comment_content.append(data_dict)

        return comment_content
