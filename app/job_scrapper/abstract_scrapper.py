import abc
from typing import Optional

from job_scrapper.query import SearchQuery


class AbstractScrapper(abc.ABC):
    def __init__(self):
        self.curr_query: Optional[SearchQuery] = None
        self.scrapped_job_list = None
        