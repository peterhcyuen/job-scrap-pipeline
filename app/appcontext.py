from typing import Any, List

from dotdict import DotDict
from job_scrapper.indeed_scrapper import IndeedScraper
from job_scrapper.linkedin_scrapper import LinkedInScrapper


class AppContext:
    llm: Any
    config: DotDict
    linkedin_scrapper: LinkedInScrapper
    linkedin_searched_ids: List[str]
    indeed_scrapper: IndeedScraper
    indeed_searched_ids: List[str]
