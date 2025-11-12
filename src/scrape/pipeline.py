"""
Scraping pipeline component for DiscourseKG platform.

Simple scraping function that will be called by an orchestrator.
"""

from src.scrape.scraper import Scraper
from src.scrape.models import ScrapeContext
from src.shared.pipeline_definitions import StageResult


def scrape_content(processing_context: ScrapeContext) -> StageResult:
    """Scrape content from the provided processing context."""
    return Scraper().scrape_content(processing_context)
