import time
from langchain_core.prompts import ChatPromptTemplate
from engine.llm_prompt import SYS_PROMPT, SKILL_JOB_TEMPLATE

class LLMService:
    def __init__(self, llm_client):
        self.llm = llm_client

    def ask_llm(self, work_exp: str, skillset: str, job_description: str) -> str:
        chat_prompt = ChatPromptTemplate.from_messages([
            ("system", SYS_PROMPT),
            ("human", SKILL_JOB_TEMPLATE)
        ])

        formatted_prompt = chat_prompt.invoke(
            {
                'work_exp': work_exp,
                'skill': skillset,
                'job_ad': job_description
            }
        )

        response = self.llm.invoke(formatted_prompt)
        time.sleep(5)
        return response.content