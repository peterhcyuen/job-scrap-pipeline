from typing import Any, List

from app.dotdict import DotDict
from job_scrapper.linkedin_scrapper import LinkedInScrapper


class AppContext:
    llm: Any
    config: DotDict
    linkedin_scrapper: LinkedInScrapper
    linkedin_searched_ids: List[str]
