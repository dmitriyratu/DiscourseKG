"""
Scraping pipeline component for DiscourseKG platform.

Simple scraping function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.scrape.scraper import Scraper


def scrape_content(processing_context: Dict[str, Any]) -> Dict[str, Any]:
    """Scrape content from the provided processing context."""
    return Scraper().scrape_content(processing_context)
