import logging
import math
import time

from DrissionPage._elements.none_element import NoneElement

from dotdict import DotDict
from .abstract_scrapper import AbstractScrapper
from .job_attribute import JobAttr

logger = logging.getLogger(__name__)


class IndeedScraper(AbstractScrapper):
    def __init__(self, selenium_config: DotDict, indeed_url: str):
        super().__init__(selenium_config)
        self.indeed_url = indeed_url
        self.job_id_list = []

    def reset(self):
        super().reset()
        self.job_id_list = []

    def _build_url(self) -> str:
        url = self.indeed_url + "/jobs?q={}&l={}"
        job_title_formatted = self.curr_query.job_title.replace(" ", "%20")
        location_formatted = self.curr_query.location.replace(" ", "%20").replace(",", "%2C+")
        url = url.format(job_title_formatted, location_formatted)

        if self.curr_query.hours_within is not None:
            url += f"&fromage={math.ceil(self.curr_query.hours_within / 24)}"

        return url

    def _scrap_job(self, job_id: str):
        job_url = f'{self.indeed_url}/viewjob?jk={job_id}'
        self._load_page(job_url)
        company_name = self.driver.find(['css:div[data-company-name="true"] a', 'css:div[data-company-name="true"] span'])[1].text
        job_title = self.driver.ele('css:.jobsearch-JobInfoHeader-title > span').text
        location = self.driver.ele('css:div[data-testid="inlineHeader-companyLocation"]').text
        job_description = self.driver.ele('@id:jobDescriptionText').text

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

    def _collect_job_ids(self):
        logger.info("Start collecting job ids")
        while True:
            job_cards = self.driver.eles('css:#mosaic-provider-jobcards > ul > li')
            for job_card in job_cards:
                list_a_tag = job_card.eles('css:a')
                if list_a_tag:
                    self.job_id_list.append(job_card.ele('css:a').attr('data-jk'))

            next_page = self.driver.ele("css:a[data-testid='pagination-page-next']")
            if next_page is None or isinstance(next_page, NoneElement):
                break

            self._click_page(next_page)
            self.driver._wait_loaded(5)
        logger.info("End collecting job ids")

    def _search_query(self):
        search_url = self._build_url()
        logger.info(f"Search URL: {search_url}")
        self._load_page(search_url)
        self._collect_job_ids()
        for job_id in self.job_id_list:
            self._scrap_job(job_id)
            time.sleep(1)
            if self.job_counter >= self.curr_query.num_jobs:
                logger.info(f"Stop searching as current job count already reach {self.curr_query.num_jobs}")
                self.curr_query_finished = True
                break
