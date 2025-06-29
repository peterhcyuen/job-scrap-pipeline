import logging
import pandas as pd
from tqdm import tqdm
from engine.models import Task
from scrapers.job_attribute import JobAttr
from services.llm_service import LLMService

logger = logging.getLogger(__name__)

class TaskExecutor:
    def __init__(self, llm_service: LLMService):
        self.llm_service = llm_service

    def execute(self, task: Task, scraper, history: list) -> pd.DataFrame:
        df_jobs = scraper.search(task.search_queries)
        df_jobs['site'] = task.site_name
        if history:
            logger.info("Filter out jobs that already being searched previously")
            df_jobs = df_jobs[~df_jobs[JobAttr.JOB_ID].isin(history)]

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
                    result = self.llm_service.ask_llm(task.work_exp, task.skillset, job_description)
                except Exception as e:
                    logger.error(e)
                    continue

                if result.lower() == 'good':
                    good_ids.append(job_id)
                    llm_response_normal_ids.append(job_id)
                elif result.lower() == 'moderate':
                    moderate_ids.append(job_id)
                    llm_response_normal_ids.append(job_id)
                elif result.lower() == 'poor':
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