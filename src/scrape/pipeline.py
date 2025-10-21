"""
Scraping pipeline component for KG-Sentiment platform.

Simple scraping function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.scrape.scraper import Scraper


def scrape_content(item: Dict[str, Any]) -> Dict[str, Any]:
    """Scrape content from the provided item."""
    return Scraper().scrape_content(item)
