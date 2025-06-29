from scrapers.indeed_scrapper import IndeedScraper
from scrapers.linkedin_scrapper import LinkedInScrapper

class ScraperFactory:
    def __init__(self, config):
        self.config = config

    def create_scraper(self, site_name: str):
        if site_name == 'linkedin':
            return LinkedInScrapper(selenium_config=self.config.selenium)
        elif site_name == 'indeed':
            return IndeedScraper(selenium_config=self.config.selenium, indeed_url=self.config.indeed_url)
        else:
            raise ValueError(f"Unsupported site: {site_name}")