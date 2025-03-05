from dataclasses import dataclass
from enum import Enum
from typing import Optional, List


class JobType(Enum):
    FULL_TIME = 'full-time'
    PART_TIME = 'part-time'
    CONTRACT = 'contract'
    OTHER = 'other'


class ExpLevel(Enum):
    INTERNSHIP = 'internship'
    ENTRY = 'entry'
    ASSOCIATE = 'associate'
    MID_SENIOR = 'mid-senior'
    DIRECTOR = 'director'
    EXECUTIVE = 'executive'


class Workspace(Enum):
    ONSITE = 'on-site'
    REMOTE = 'remote'
    HYBRID = 'hybrid'


@dataclass
class SearchQuery:
    job_title: str
    location: str
    num_jobs: int
    fetch_description: bool
    job_type: Optional[JobType] = None
    experience_level: Optional[ExpLevel] = None
    workspace: Optional[Workspace] = None
    hours_within: Optional[int] = None
    include_words: Optional[List[str]] = None
    exclude_words: Optional[List[str]] = None
    exclude_companies: Optional[List[str]] = None
