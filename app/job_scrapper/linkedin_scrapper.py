import logging
import time

from DrissionPage._elements.none_element import NoneElement

from dotdict import DotDict
from .abstract_scrapper import AbstractScrapper
from .job_attribute import JobAttr
from .query import ExpLevel, JobType, Workspace

logger = logging.getLogger(__name__)


class LinkedInScrapper(AbstractScrapper):
    def __init__(self, selenium_config: DotDict):
        super().__init__(selenium_config)

        # Dictionary to map user-friendly experience levels to LinkedIn's filter values
        self.experience_level_mapping = {
            ExpLevel.INTERNSHIP: "1",
            ExpLevel.ENTRY: "2",
            ExpLevel.ASSOCIATE: "3",
            ExpLevel.MID_SENIOR: "4",
            ExpLevel.DIRECTOR: "5",
            ExpLevel.EXECUTIVE: "6"
        }

        # Dictionary to map user-friendly job types to LinkedIn's filter values
        self.job_type_mapping = {
            JobType.FULL_TIME: "F",
            JobType.PART_TIME: "P",
            JobType.CONTRACT: "C",
            JobType.OTHER: "O"
        }

        # Dictionary to map user-friendly workplace types to LinkedIn's filter values
        self.workplace_mapping = {
            Workspace.ONSITE: "1",
            Workspace.REMOTE: "2",
            Workspace.HYBRID: "3"
        }

    def _build_url(self) -> str:
        if self.curr_query.custom_url:
            return self.curr_query.custom_url

        base_url = "https://www.linkedin.com/jobs/search/?keywords={}&location={}"

        job_title_formatted = self.curr_query.job_title.replace(" ", "%20")
        location_formatted = self.curr_query.location.replace(" ", "%20")
        url = base_url.format(job_title_formatted, location_formatted)

        if self.curr_query.hours_within is not None:
            url += f"&f_TPR=r{self.curr_query.hours_within * 3600}"

        # Add experience level filter if provided
        if self.curr_query.experience_level is not None:
            url += f"&f_E={self.experience_level_mapping[self.curr_query.experience_level]}"

        # Add job type filter if provided
        if self.curr_query.job_type is not None:
            url += f"&f_JT={self.job_type_mapping[self.curr_query.job_type]}"

        # Add workplace type filter if provided
        if self.curr_query.workspace is not None:
            url += f"&f_WT={self.workplace_mapping[self.curr_query.workspace]}"

        return url

    def _scrap_job(self, job_id: str):
        company_name = None
        if (company_name_dom := self.driver.find(["css:div.job-details-jobs-unified-top-card__company-name > a", "css:div.job-details-jobs-unified-top-card__company-name"])[1]) is not None:
            company_name = company_name_dom.text.strip()
        location = self.driver.eles("css:div.job-details-jobs-unified-top-card__primary-description-container > div > span")[0].text
        job_title = self.driver.ele("css:div.job-details-jobs-unified-top-card__job-title > h1 > a").text.strip()
        job_description = self.driver.ele("@id:job-details").text

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
            JobAttr.JOB_URL: f"https://www.linkedin.com/jobs/view/{job_id}",
            # JobAttr.WORKSPACE: workspace,
            # JobAttr.JOB_TYPE: job_type,
            JobAttr.JOB_DESC: job_description if self.curr_query.fetch_description else ""
        })

    def _scrap_page(self):
        logger.info(f"Searching page {self.page_counter + 1}")
        scroll_list = self.driver.ele('css:div.scaffold-layout__list > div')
        self._page_scroll(scroll_list)
        job_ul = self.driver.ele("css:#main > div > div.scaffold-layout__list-detail-inner.scaffold-layout__list-detail-inner--grow > div.scaffold-layout__list > div > ul")
        job_cards = job_ul.eles('css:li.scaffold-layout__list-item')
        for job_card in job_cards:
            job_card.ele("tag:a").click()
            self.driver._wait_loaded(5)
            time.sleep(1)
            self._scrap_job(job_card.attr("data-occludable-job-id"))

            if self.job_counter >= self.curr_query.num_jobs:
                logger.info(f"Stop searching as current job count already reach {self.curr_query.num_jobs}")
                self.curr_query_finished = True
                break

        self.page_counter += 1

    def _search_query(self):
        search_url = self._build_url()
        logger.info(f"Search URL: {search_url}")
        self._load_page(search_url)
        time.sleep(5)

        while not self.curr_query_finished:
            self._scrap_page()
            next_button = self.driver.ele('css:button.jobs-search-pagination__button--next')
            if next_button is not None and not isinstance(next_button, NoneElement):
                next_button.click()
                self.driver._wait_loaded(5)
                time.sleep(2)
            else:
                break
