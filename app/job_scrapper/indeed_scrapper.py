import logging
import math
import time

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from .abstract_scrapper import AbstractScrapper
from .job_attribute import JobAttr

logger = logging.getLogger(__name__)


class IndeedScraper(AbstractScrapper):
    def __init__(self, indeed_url: str, user_data_dir: str = None, show_browser=False):
        super().__init__(user_data_dir, show_browser)
        self.indeed_url = indeed_url

    def _build_url(self) -> str:
        url = self.indeed_url + "/jobs?q={}&l={}"
        job_title_formatted = self.curr_query.job_title.replace(" ", "%20")
        location_formatted = self.curr_query.location.replace(" ", "%20").replace(",", "%2C+")
        url = url.format(job_title_formatted, location_formatted)

        if self.curr_query.hours_within is not None:
            url += f"&fromage={math.ceil(self.curr_query.hours_within / 24)}"

        return url

    def _scrap_job(self, job_card: WebElement):
        job_id = job_card.find_element(By.CSS_SELECTOR, "a").get_attribute("data-jk")
        company_name = self.driver.find_element(By.CSS_SELECTOR, 'div[data-company-name="true"] a').text
        job_title = self.driver.find_element(By.CSS_SELECTOR, ".jobsearch-JobInfoHeader-title > span").text
        location = self.driver.find_element(By.CSS_SELECTOR, 'div[data-testid="inlineHeader-companyLocation"]').text
        job_description = self.driver.find_element(By.CSS_SELECTOR, "#jobDescriptionText").text

        logger.info(f"Company: {company_name}, Job Title: {job_title}")

        if self.curr_query.exclude_companies and company_name in self.curr_query.exclude_companies:
            logger.info(f"Skip this job as {company_name} in the list of excluded companies")
            return

        if self.curr_query.include_words and not any(kw.lower() in job_title.lower() for kw in self.curr_query.include_words):
            logger.info(f"Skip this job as {job_title} does not include the required key words in {self.curr_query.include_words}")
            return

        if self.curr_query.exclude_words and any(kw.lower() in job_title.lower() for kw in self.curr_query.exclude_words):
            logger.info(f"Skip this job as {job_title} include keywords in the exclusive word list {self.curr_query.exclude_words}")
            return

        self.job_counter += 1
        self.scrapped_job_list.append({
            JobAttr.JOB_ID: job_id,
            JobAttr.SEARCH_TITLE: self.curr_query.job_title,
            JobAttr.COMPANY: company_name,
            JobAttr.JOB_TITLE: job_title,
            JobAttr.LOCATION: location,
            JobAttr.JOB_URL: f"{self.indeed_url}/viewjob?jk={job_id}",
            JobAttr.JOB_DESC: job_description if self.curr_query.fetch_description else ""
        })

    def _scrap_page(self):
        logger.info(f"Searching page {self.page_counter + 1}")
        job_cards = self.driver.find_elements(By.CSS_SELECTOR, "#mosaic-provider-jobcards > ul > li")
        for job_card in job_cards:
            try:
                list_a_tag = job_card.find_elements(By.CSS_SELECTOR, "a")
                if list_a_tag:
                    job_card.find_elements(By.CSS_SELECTOR, "li a")[0].click()
                    WebDriverWait(self.driver, 5).until(
                        lambda web_driver: web_driver.execute_script('return document.readyState') == 'complete'
                    )
                    time.sleep(2)
                    # time.sleep(random.choice(list(range(2, 11))))
                    self._scrap_job(job_card)
                    self.driver.execute_script("window.scrollBy(0, 500);")
            except NoSuchElementException as e:
                logger.error(e)

            if self.job_counter >= self.curr_query.num_jobs:
                logger.info(f"Stop searching as current job count already reach {self.curr_query.num_jobs}")
                self.curr_query_finished = True
                break

        self.page_counter += 1

    def _search_query(self):
        search_url = self._build_url()
        logger.info(f"Search URL: {search_url}")
        self._load_page(search_url)

        while not self.curr_query_finished:
            next_page = self._find_element_by([(By.CSS_SELECTOR, "a[data-testid='pagination-page-next']")])
            self._scrap_page()

            if next_page is None:
                break

            next_page.click()
            WebDriverWait(self.driver, 10).until(
                lambda web_driver: web_driver.execute_script('return document.readyState') == 'complete'
            )
            time.sleep(2)
