import os
from typing import List


class JobHistoryService:
    def __init__(self, history_dir='historical_job_ids'):
        self.history_dir = history_dir
        self.linkedin_history_path = os.path.join(self.history_dir, "linkedin_job_ids.txt")
        self.indeed_history_path = os.path.join(self.history_dir, "indeed_job_ids.txt")
        self.jobsdb_history_path = os.path.join(self.history_dir, "jobsdb_job_ids.txt")
        self._ensure_history_files_exist()

    def _ensure_history_files_exist(self):
        os.makedirs(self.history_dir, exist_ok=True)
        if not os.path.exists(self.linkedin_history_path):
            with open(self.linkedin_history_path, 'w', encoding='utf-8') as f:
                pass
        if not os.path.exists(self.indeed_history_path):
            with open(self.indeed_history_path, 'w', encoding='utf-8') as f:
                pass
        if not os.path.exists(self.jobsdb_history_path):
            with open(self.jobsdb_history_path, 'w', encoding='utf-8') as f:
                pass

    def get_linkedin_history(self) -> List[str]:
        with open(self.linkedin_history_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file]

    def get_indeed_history(self) -> List[str]:
        with open(self.indeed_history_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file]

    def get_jobsdb_history(self) -> List[str]:
        with open(self.jobsdb_history_path, 'r', encoding='utf-8') as file:
            return [line.strip() for line in file]

    def save_linkedin_history(self, job_ids: List[str]):
        with open(self.linkedin_history_path, 'a', encoding='utf-8') as f:
            for job_id in job_ids:
                f.write(job_id + '\n')

    def save_indeed_history(self, job_ids: List[str]):
        with open(self.indeed_history_path, 'a', encoding='utf-8') as f:
            for job_id in job_ids:
                f.write(job_id + '\n')

    def save_jobsdb_history(self, job_ids: List[str]):
        with open(self.jobsdb_history_path, 'a', encoding='utf-8') as f:
            for job_id in job_ids:
                f.write(job_id + '\n')
