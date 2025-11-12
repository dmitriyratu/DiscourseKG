"""
Scraper implementation for DiscourseKG platform.

This class handles the scraping of speaker transcripts from web sources.
Currently uses mock data generation - will be replaced with real scraping.
"""

from typing import Dict, Any
from tests.transcript_generator import generate_test_transcript
from src.utils.logging_utils import get_logger
from src.scrape.models import ScrapingResult, ScrapingData, ScrapeContext
from src.shared.pipeline_definitions import StageResult

logger = get_logger(__name__)


class Scraper:
    """
    Scraper implementation for collecting speaker content.
    
    This class handles the scraping of content from web sources for the
    knowledge graph platform. Currently uses mock data generation but
    will be replaced with real web scraping functionality.
    """
    
    def __init__(self):
        logger.debug("Scraper initialized")
    
    def scrape_content(self, processing_context: ScrapeContext) -> StageResult:
        """Scrape content from the provided processing context."""
        logger.debug(f"Starting scraping for URL: {processing_context.source_url}")
        
        # TODO: Replace with real web scraping
        # For now, generate mock data
        scrape_data = generate_test_transcript(
            {'id': processing_context.id, 'source_url': processing_context.source_url}, 
            'speech'  # Mock default
        )
        
        return self._create_result(scrape_data)
    
    def _create_result(self, scrape_data: Dict[str, Any]) -> StageResult:
        """Helper to create StageResult with separated artifact and metadata."""
        
        scrape_text = scrape_data['scrape']
        scraping_data = ScrapingData(
            scrape=scrape_text,
            word_count=len(scrape_text.split()) if scrape_text else 0,
            title=scrape_data.get('title'),
            content_date=scrape_data.get('content_date')
        )
        
        # Build artifact (what gets persisted)
        artifact = ScrapingResult(
            id=scrape_data['id'],
            success=True,
            data=scraping_data,
            error_message=None
        )
        
        # Extract metadata (for state updates only)
        metadata = {
            "title": scrape_data.get("title"),
            "content_date": scrape_data.get("content_date"),
        }
        
        logger.debug(f"Successfully scraped: {artifact.id} - {scraping_data.word_count} words")
        return StageResult(artifact=artifact.model_dump(), metadata=metadata)
