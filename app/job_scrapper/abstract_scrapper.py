import abc
import logging
import time
from typing import Optional, List, Tuple

import pandas as pd
from selenium import webdriver
from selenium.common import TimeoutException, NoSuchElementException, ElementNotInteractableException
from selenium.webdriver import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options as FireFoxOptions
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from dotdict import DotDict
from .job_attribute import JobAttr
from .query import SearchQuery

logger = logging.getLogger(__name__)


class AbstractScrapper(abc.ABC):
    def __init__(self, selenium_config: DotDict):
        if selenium_config.browser == 'chrome':
            browser_config = selenium_config.chrome
            self.options = Options()
            self.options.add_argument("--disable-gpu")
            self.options.add_argument("--disable-notifications")
            self.options.add_argument("--no-sandbox")
            self.options.add_argument("--disable-dev-shm-usage")
            self.options.add_argument("--disable-extensions")
            if not browser_config.show_browser:
                self.options.add_argument("--headless")  # Run in headless mode (no browser UI)
            if browser_config.user_data_dir:
                self.options.add_argument(f"--user-data-dir={browser_config.user_data_dir}")
                self.options.add_argument(f"--profile-directory={browser_config.profile}")
            if 'binary_path' in browser_config:
                self.options.binary_location = browser_config.binary_path
        elif selenium_config.browser == 'firefox':
            browser_config = selenium_config.firefox
            self.options = FireFoxOptions()
            if not browser_config.show_browser:
                self.options.headless = True
            self.options.profile = browser_config.profile_dir
            self.options.set_preference("layers.acceleration.disabled", True)
            self.options.set_preference("dom.webnotifications.enabled", False)
            self.options.set_preference("dom.webdriver.enabled", False)
            self.options.set_preference('useAutomationExtension', False)
        else:
            raise ValueError(f"Unsupported browser: {selenium_config.browser}")

        self.browser = selenium_config.browser
        self.driver: Optional[WebDriver] = None
        self.curr_query: Optional[SearchQuery] = None
        self.scrapped_job_list = []
        self.job_counter = 0
        self.page_counter = 0
        self.curr_query_finished = False

    def reset(self):
        self.job_counter = 0
        self.page_counter = 0
        self.curr_query_finished = False

    def _load_page(self, url):
        try:
            self.driver.get(url)
            # Wait for a specific element that indicates the page has loaded
            WebDriverWait(self.driver, 10).until(
                lambda web_driver: web_driver.execute_script('return document.readyState') == 'complete'
            )
            print("Page loaded successfully.")
        except TimeoutException:
            print("Page load timed out. Reloading the page...")
            # driver.refresh()
            self._load_page(url)

    def _find_element_by(self, selectors: List[Tuple]) -> Optional[WebElement]:
        for select in selectors:
            try:
                return self.driver.find_element(select[0], select[1])
            except NoSuchElementException as e:
                logger.error(e)

        return None

    def _page_scroll(self, web_element: WebElement):
        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", web_element)
        time.sleep(1)
        try:
            while True:
                web_element.send_keys(Keys.PAGE_UP)
                time.sleep(1)
                scroll_top = self.driver.execute_script("return arguments[0].scrollTop", web_element)
                if scroll_top <= 0:
                    break
        except ElementNotInteractableException as e:
            logger.error(e)

    def _build_url(self) -> str:
        raise NotImplementedError

    def _scrap_job(self, job_card: WebElement):
        raise NotImplementedError

    def _scrap_page(self):
        raise NotImplementedError

    def _search_query(self):
        raise NotImplementedError

    def search(self, queries: List[SearchQuery]) -> pd.DataFrame:
        self.scrapped_job_list = []

        if self.browser == 'chrome':
            self.driver = webdriver.Chrome(options=self.options)
        elif self.browser == 'firefox':
            self.driver = webdriver.Firefox(options=self.options)

        for query in queries:
            logger.info(f"Starting searching {query.job_title}")
            self.reset()
            self.curr_query = query
            self._search_query()

        logger.info(f"Scrapped jobs count: {len(self.scrapped_job_list)}")
        df_jobs = None
        if self.scrapped_job_list:
            df_jobs = pd.DataFrame(self.scrapped_job_list)
            df_jobs = df_jobs.drop_duplicates(subset=[JobAttr.JOB_ID])
            logger.info(f"Filter out duplicated jobs. Final scrapped jobs count: {df_jobs.shape[0]}")

        self.driver.quit()

        return df_jobs
