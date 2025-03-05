import logging
import time
from dataclasses import dataclass
from typing import List

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from tqdm import tqdm

from appcontext import AppContext
from job_scrapper.job_attribute import JobAttr
from job_scrapper.query import SearchQuery
from task.llm_prompt import SYS_PROMPT, SKILL_JOB_TEMPLATE

logger = logging.getLogger(__name__)


@dataclass
class Task:
    skillset: str
    llm_filter: bool
    site_name: str
    search_queries: List[SearchQuery]


def ask_llm(skillset: str, job_description: str) -> str:
    llm = AppContext.llm
    chat_prompt = ChatPromptTemplate.from_messages([
        ("system", SYS_PROMPT),
        ("human", SKILL_JOB_TEMPLATE)
    ])

    formatted_prompt = chat_prompt.invoke(
        {
            'skill': skillset,
            'job_ad': job_description
        }
    )

    response = llm.invoke(formatted_prompt.messages)
    time.sleep(5)
    return response.content


def execute_task(task: Task) -> pd.DataFrame:
    df_jobs = pd.DataFrame([])
    if task.site_name == 'linkedin':
        df_jobs = AppContext.linkedin_scrapper.search(task.search_queries)
        df_jobs['site'] = task.site_name
        if AppContext.linkedin_searched_ids:
            logger.info("Filter out jobs that already being searched previously")
            df_jobs = df_jobs[~df_jobs[JobAttr.JOB_ID].isin(AppContext.linkedin_searched_ids)]

    logging.info(f"Searched job count: {df_jobs.shape[0]}")

    if df_jobs.empty:
        return df_jobs

    if task.llm_filter:
        logger.info("Start asking LLM loop")
        good_ids = []
        moderate_ids = []
        poor_ids = []
        llm_response_normal_ids = []
        for _, row in tqdm(df_jobs.iterrows(), total=len(df_jobs), desc="LLM Matching Loop"):
            job_id = row[JobAttr.JOB_ID]
            job_description = row[JobAttr.JOB_DESC]
            try:
                result = ask_llm(task.skillset, job_description)
            except Exception as e:
                logger.error(e)
                continue

            if result.lower() == 'good fit':
                good_ids.append(job_id)
                llm_response_normal_ids.append(job_id)
            elif result.lower() == 'moderate fit':
                moderate_ids.append(job_id)
                llm_response_normal_ids.append(job_id)
            elif result.lower() == 'poor fit':
                poor_ids.append(job_id)
                llm_response_normal_ids.append(job_id)
            else:
                logger.error("LLM cannot response properly. ")
                logger.info(f"LLM response: {result}")
                logger.info(f"Job Title: {row.title}, Company: {row.company}, URL: {row.job_url}")

        df_jobs = df_jobs[df_jobs[JobAttr.JOB_ID].isin(llm_response_normal_ids)]
        df_jobs['validate_result'] = False
        df_jobs.loc[df_jobs[JobAttr.JOB_ID].isin(good_ids + moderate_ids), 'validate_result'] = True
        df_jobs.loc[df_jobs[JobAttr.JOB_ID].isin(good_ids), 'llm_comment'] = 'Good'
        df_jobs.loc[df_jobs[JobAttr.JOB_ID].isin(moderate_ids), 'llm_comment'] = 'Moderate'
        df_jobs.loc[df_jobs[JobAttr.JOB_ID].isin(poor_ids), 'llm_comment'] = 'Poor'
    else:
        df_jobs['validate_result'] = True

    df_jobs = df_jobs.drop(columns=[JobAttr.JOB_DESC])

    return df_jobs


def execute_task_list(tasks: List[Task]):
    list_dfs = []
    for i, task in enumerate(tasks):
        logger.info(f"Executing task {i + 1}")
        df = execute_task(task)
        if not df.empty:
            list_dfs.append(df)

    if list_dfs:
        df_jobs = pd.concat(list_dfs, ignore_index=True)
        df_jobs = df_jobs.drop_duplicates(subset=[JobAttr.JOB_ID])
        return df_jobs

    return pd.DataFrame([])
