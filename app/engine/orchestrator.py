import logging
from datetime import datetime
import pandas as pd
from scrapers.job_attribute import JobAttr
from engine.models import Task, SearchQuery, JobType, ExpLevel
from engine.executor import TaskExecutor
from services.config_service import ConfigService
from services.history_service import JobHistoryService
from services.scraper_factory import ScraperFactory
from common.dotdict import DotDict
import os

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, config_service: ConfigService, history_service: JobHistoryService, scraper_factory: ScraperFactory, task_executor: TaskExecutor):
        self.config_service = config_service
        self.history_service = history_service
        self.scraper_factory = scraper_factory
        self.task_executor = task_executor
        self.config = self.config_service.get_config()

    def _create_tasks(self):
        logger.info("Creating tasks")
        task_list = []
        for task_config in self.config.tasks:
            task = DotDict(task_config)
            with open(os.path.join('skillset', task.skillset), 'r', encoding='utf-8') as file:
                skillset_str = file.read()
            with open(os.path.join('skillset', task.work_exp), 'r', encoding='utf-8') as file:
                work_exp_str = file.read()
            query_list = []
            for query in task.queries:
                query = DotDict(query)
                query_list.append(
                    SearchQuery(
                        job_title=query.job_title,
                        location=query.location,
                        num_jobs=query.num_jobs,
                        custom_url=query.custom_url,
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
                    work_exp=work_exp_str,
                    llm_filter=task.llm_filter,
                    site_name=task.site_name,
                    search_queries=query_list
                )
            )
        logger.info(f"Created {len(task_list)} task(s)")
        return task_list

    def run(self):
        tasks = self._create_tasks()
        list_dfs = []
        for i, task in enumerate(tasks):
            logger.info(f"Executing task {i + 1}")
            scraper = self.scraper_factory.create_scraper(task.site_name)
            history = []
            if task.site_name == 'linkedin':
                history = self.history_service.get_linkedin_history()
            elif task.site_name == 'indeed':
                history = self.history_service.get_indeed_history()

            df = self.task_executor.execute(task, scraper, history)
            if not df.empty:
                list_dfs.append(df)
                if task.site_name == 'linkedin':
                    self.history_service.save_linkedin_history(df['Job ID'].tolist())
                elif task.site_name == 'indeed':
                    self.history_service.save_indeed_history(df['Job ID'].tolist())

        if list_dfs:
            df_jobs = pd.concat(list_dfs, ignore_index=True)
            df_jobs = df_jobs.drop_duplicates(subset=['Job ID'])
            df_jobs = df_jobs[
                [JobAttr.SEARCH_TITLE,
                'site',
                JobAttr.JOB_TITLE,
                JobAttr.COMPANY,
                JobAttr.JOB_URL,
                JobAttr.LOCATION,
                'llm_comment',
                'validate_result']
            ]
            df_jobs = df_jobs.sort_values(by=['site', JobAttr.SEARCH_TITLE, JobAttr.COMPANY])
            df_jobs.to_csv(os.path.join('scrapped_jobs', f"{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"), index=False)