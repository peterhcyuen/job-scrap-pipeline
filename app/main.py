import argparse
import logging
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from engine.orchestrator import Orchestrator
from engine.executor import TaskExecutor
from services.config_service import ConfigService
from services.history_service import JobHistoryService
from services.llm_service import LLMService
from services.scraper_factory import ScraperFactory

logger = logging.getLogger(__name__)

def setup_llm(config):
    logger.info("Setup LLM")
    if config.llm.provider == 'ollama':
        return ChatOllama(model=config.llm.model, temperature=0.2, num_ctx=8192)
    elif config.llm.provider == 'gemini':
        os.environ['GOOGLE_API_KEY'] = config.llm.api_key
        return ChatGoogleGenerativeAI(
            model=config.llm.model,
            temperature=0.2,
            max_tokens=None,
            max_retries=3
        )
    else:
        raise ValueError("Currently only support ollama and gemini")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/config.yml")
    args = parser.parse_args()

    config_service = ConfigService(config_path=args.config)
    config = config_service.get_config()

    llm_client = setup_llm(config)
    llm_service = LLMService(llm_client)
    history_service = JobHistoryService()
    scraper_factory = ScraperFactory(config)
    task_executor = TaskExecutor(llm_service)

    orchestrator = Orchestrator(
        config_service=config_service,
        history_service=history_service,
        scraper_factory=scraper_factory,
        task_executor=task_executor
    )

    orchestrator.run()
