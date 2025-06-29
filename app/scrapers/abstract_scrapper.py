import abc
import logging
import time
from typing import Optional, List

import pandas as pd
from DrissionPage._configs.chromium_options import ChromiumOptions
from DrissionPage._elements.chromium_element import ChromiumElement
from DrissionPage._pages.chromium_page import ChromiumPage

from common.dotdict import DotDict
from .cloudflare_bypasser import CloudflareBypasser
from .job_attribute import JobAttr
from engine.models import SearchQuery

logger = logging.getLogger(__name__)


class AbstractScrapper(abc.ABC):
    def __init__(self, selenium_config: DotDict):
        if selenium_config.browser == 'chrome':
            browser_config = selenium_config.chrome

            self.options = ChromiumOptions()
            self.options.set_argument("--disable-gpu")
            self.options.set_argument("--disable-notifications")
            self.options.set_argument("--disable-dev-shm-usage")
            self.options.set_argument("--disable-extensions")
            if not browser_config.show_browser:
                self.options.set_argument("--headless")  # Run in headless mode (no browser UI)
            if browser_config.user_data_dir:
                self.options.set_user_data_path(browser_config.user_data_dir)
                self.options.set_user(browser_config.profile)
            if 'binary_path' in browser_config:
                self.options.set_browser_path(browser_config.binary_path)
        else:
            raise ValueError(f"Unsupported browser: {selenium_config.browser}")

        self.cf_bypasser: Optional[CloudflareBypasser] = None

        self.browser = selenium_config.browser
        self.driver: Optional[ChromiumPage] = None
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
        self.driver.get(url)
        self.driver._wait_loaded(5)

        if self.is_cloudflare_block():
            self.cf_bypasser.bypass()

    def _click_page(self, ele: ChromiumElement):
        ele.click()
        self.driver._wait_loaded(5)

        if self.is_cloudflare_block():
            self.cf_bypasser.bypass()

    def _page_scroll(self, web_element: ChromiumElement):
        self.driver.run_js("arguments[0].scrollTop = arguments[0].scrollHeight", web_element)
        time.sleep(1)
        while True:
            self.driver.run_js("arguments[0].scrollTop -= 500;", web_element)
            time.sleep(1)
            scroll_top = self.driver.run_js("return arguments[0].scrollTop", web_element)
            if scroll_top <= 0:
                break

    def _build_url(self) -> str:
        raise NotImplementedError

    def _scrap_job(self, job_id: str):
        raise NotImplementedError

    def _scrap_page(self):
        raise NotImplementedError

    def _search_query(self):
        raise NotImplementedError

    def search(self, queries: List[SearchQuery]) -> pd.DataFrame:
        self.scrapped_job_list = []

        if self.browser == 'chrome':
            self.driver = ChromiumPage(addr_or_opts=self.options)

        self.cf_bypasser = CloudflareBypasser(self.driver)

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

    def is_cloudflare_block(self):
        title = self.driver.title.lower()
        return "just a moment" in title or '請稍候...' in title
