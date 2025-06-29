import os

import yaml

from common.dotdict import DotDict
from scrapers.indeed_scrapper import IndeedScraper
from engine.models import SearchQuery, ExpLevel, JobType

if __name__ == '__main__':
    config = None
    with open(os.path.join('config', 'config.yml'), 'r') as file:
        config = DotDict(yaml.safe_load(file))

    scrapper = IndeedScraper(config.selenium, indeed_url="https://ca.indeed.com")
    queries = [
        SearchQuery(
            job_title="Software Engineer",
            location="Vancouver",
            num_jobs=9999,
            fetch_description=True,
            experience_level=ExpLevel.MID_SENIOR,
            job_type=JobType.FULL_TIME,
            hours_within=72,
            exclude_words=['fullstack', 'full-stack', 'full stack', 'frontend', 'front end', 'front-end'],
            exclude_companies=['Lumenalta']
        ),
        # SearchQuery(
        #     job_title="Machine Learning Engineer",
        #     location="Vancouver,BC",
        #     num_jobs=10,
        #     fetch_description=False,
        #     experience_level=ExpLevel.MID_SENIOR,
        #     hours_within=24,
        #     include_words=['Machine Learning', 'ML', 'artificial intelligence', 'ai'],
        #     exclude_companies=['Lumenalta']
        # )
    ]
    jobs = scrapper.search(queries)
    if jobs is not None:
        jobs.to_csv("scrapped_jobs.csv", index=False)
