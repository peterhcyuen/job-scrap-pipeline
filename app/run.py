import argparse
import logging
import os
import os.path
from datetime import datetime
from typing import List

import pandas as pd
import yaml
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama

from appcontext import AppContext
from dotdict import DotDict
from job_scrapper.job_attribute import JobAttr
from job_scrapper.linkedin_scrapper import LinkedInScrapper
from job_scrapper.query import SearchQuery, JobType, ExpLevel
from task.task import Task, execute_task_list

logger = logging.getLogger(__name__)


def setup_llm():
    logger.info("Setup LLM")
    if AppContext.config.llm.provider == 'ollama':
        AppContext.llm = ChatOllama(model=AppContext.config.llm.model, temperature=0.2, num_ctx=8192)
    elif AppContext.config.llm.provider == 'gemini':
        os.environ['GOOGLE_API_KEY'] = AppContext.config.llm.api_key
        AppContext.llm = ChatGoogleGenerativeAI(
            model=AppContext.config.llm.model,
            temperature=0.2,
            max_tokens=None,
            max_retries=3
        )
    else:
        raise ValueError("Currently only support ollama")


def setup_scrapper():
    AppContext.linkedin_scrapper = LinkedInScrapper(user_data_dir=AppContext.config.selenium.user_data_dir,
                                                    show_browser=AppContext.config.selenium.show_browser)


def create_task() -> List[Task]:
    logger.info("Creating tasks")
    task_list = []
    for task in AppContext.config.tasks:
        task = DotDict(task)
        with open(os.path.join('skillset', task.skillset), 'r', encoding='utf-8') as file:
            skillset_str = file.read()
        query_list = []
        for query in task.queries:
            query = DotDict(query)
            query_list.append(
                SearchQuery(
                    job_title=query.job_title,
                    location=query.location,
                    num_jobs=query.num_jobs,
                    fetch_description=query.fetch_description,
                    job_type=JobType(query.job_type),
                    experience_level=ExpLevel(query.experience_level),
                    hours_within=query.hours_within,
                    include_words=query.include_words,
                    exclude_words=query.exclude_words,
                    exclude_companies=task.excluded_companies
                )
            )
        task_list.append(
            Task(
                skillset=skillset_str,
                llm_filter=task.llm_filter,
                site_name=task.site_name,
                search_queries=query_list
            )
        )

    logger.info(f"Created {len(task_list)} task(s)")
    return task_list


def post_scrapped_jobs(jobs: pd.DataFrame):
    all_jobs_id = jobs[JobAttr.JOB_ID].tolist()
    with open(os.path.join("historical_job_ids", "linkedin_job_ids.txt"), 'a', encoding='utf-8') as f:
        for job_id in all_jobs_id:
            f.write(job_id + '\n')

    jobs = jobs[
        [JobAttr.SEARCH_TITLE,
         'site',
         JobAttr.JOB_TITLE,
         JobAttr.COMPANY,
         JobAttr.JOB_URL,
         JobAttr.LOCATION,
         'llm_comment',
         'validate_result']
    ]
    jobs = jobs.sort_values(by=['site', JobAttr.SEARCH_TITLE, 'llm_comment'])
    jobs.to_csv(os.path.join('scrapped_jobs', f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"), index=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config.yml")
    args = parser.parse_args()

    with open(os.path.join('config', args.config), 'r') as file:
        AppContext.config = DotDict(yaml.safe_load(file))

    linkedin_id_path = os.path.join("historical_job_ids", "linkedin_job_ids.txt")
    if not os.path.exists(linkedin_id_path):
        os.makedirs(os.path.dirname(linkedin_id_path), exist_ok=True)
        with open(linkedin_id_path, 'w', encoding='utf-8') as f:
            pass
        AppContext.linkedin_searched_ids = []
    else:
        with open(linkedin_id_path, 'r', encoding='utf-8') as file:
            AppContext.linkedin_searched_ids = [line.strip() for line in file]

    setup_llm()
    setup_scrapper()

    tasks = create_task()
    df_jobs = execute_task_list(tasks)
    if not df_jobs.empty:
        post_scrapped_jobs(df_jobs)
