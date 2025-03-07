import logging
import time

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.wait import WebDriverWait

from .abstract_scrapper import AbstractScrapper
from .job_attribute import JobAttr
from .query import SearchQuery, ExpLevel, JobType, Workspace

logger = logging.getLogger(__name__)


class LinkedInScrapper(AbstractScrapper):
    def __init__(self, user_data_dir: str = None, show_browser=False):
        super().__init__(user_data_dir, show_browser)

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

    def _scrap_job(self, job_card: WebElement):
        job_id = job_card.get_attribute("data-occludable-job-id")
        company_name = None
        if (company_name_dom := self._find_element_by([(By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__company-name > a"),
                                                       (By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__company-name")])) is not None:
            company_name = company_name_dom.text.strip()
        location = self.driver.find_elements(By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__primary-description-container > div > span")[0].text
        job_title = self.driver.find_element(By.CSS_SELECTOR, "div.job-details-jobs-unified-top-card__job-title > h1 > a").text.strip()
        # workspace = self.driver.find_element(By.CSS_SELECTOR,
        #                                      "div.relative.job-details-jobs-unified-top-card__container--two-pane > div > button > div:nth-child(2) > span > span:nth-child(1)").text.strip()
        # job_type = self.driver.find_element(By.CSS_SELECTOR,
        #                                     "div.relative.job-details-jobs-unified-top-card__container--two-pane > div > button > div:nth-child(3) > span > span:nth-child(1)").text.strip()
        job_description = self.driver.find_element(By.ID, "job-details").text

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
        scroll_list = self.driver.find_element(By.CSS_SELECTOR, "div.scaffold-layout__list > div")
        self._page_scroll(scroll_list)
        job_ul = self.driver.find_element(By.CSS_SELECTOR, "#main > div > div.scaffold-layout__list-detail-inner.scaffold-layout__list-detail-inner--grow > div.scaffold-layout__list > div > ul")
        job_cards = job_ul.find_elements(By.CSS_SELECTOR, 'li.scaffold-layout__list-item')
        for job_card in job_cards:
            try:
                job_card.find_element(By.TAG_NAME, "a").click()
                WebDriverWait(self.driver, 5).until(
                    lambda web_driver: web_driver.execute_script('return document.readyState') == 'complete'
                )
                time.sleep(1)
                self._scrap_job(job_card)
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
            self._scrap_page()
            pagination = self._find_element_by([(By.CSS_SELECTOR, "ul.artdeco-pagination__pages")])
            if pagination is None:
                break
            active_page = pagination.find_element(By.CSS_SELECTOR, "li.active")
            page_list = pagination.find_elements(By.CSS_SELECTOR, "li")
            cur_idx = page_list.index(active_page)
            if cur_idx < len(page_list) - 1:
                next_page = page_list[cur_idx + 1]
                next_page.click()
                WebDriverWait(self.driver, 10).until(
                    lambda web_driver: web_driver.execute_script('return document.readyState') == 'complete'
                )
                time.sleep(2)
            else:
                break


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    scrapper = LinkedInScrapper(user_data_dir="C:\\Users\\hcyue\\AppData\\Local\\Google\\Chrome\\User Data", show_browser=True)
    queries = [
        SearchQuery(
            job_title="Software Engineer",
            location="Vancouver",
            num_jobs=10,
            fetch_description=False,
            experience_level=ExpLevel.MID_SENIOR,
            job_type=JobType.FULL_TIME,
            hours_within=24,
            exclude_words=['fullstack', 'full-stack', 'full stack', 'frontend', 'front end', 'front-end'],
            exclude_companies=['Lumenalta']
        ),
        SearchQuery(
            job_title="Machine Learning Engineer",
            location="Vancouver",
            num_jobs=10,
            fetch_description=False,
            experience_level=ExpLevel.MID_SENIOR,
            hours_within=24,
            include_words=['Machine Learning', 'ML', 'artificial intelligence', 'ai'],
            exclude_companies=['Lumenalta']
        )
    ]
    jobs = scrapper.search(queries)
    if jobs is not None:
        jobs.to_csv("scrapped_jobs.csv", index=False)
