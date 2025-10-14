"""
Scrape endpoint for collecting speaker transcripts.
"""

from datetime import datetime
from typing import Dict, Any
from pathlib import Path

from src.shared.pipeline_state import PipelineStateManager
from src.shared.logging_utils import setup_logger
from src.shared.persistence import save_data
from tests.test_transcript_generator import generate_test_transcript

logger = setup_logger("ScrapeEndpoint", "scrape_flow.log")


class ScrapeEndpoint:
    """Endpoint for scraping speaker transcripts."""
    
    def __init__(self):
        self.state_manager = PipelineStateManager()
    
    def execute(self, url: str, speaker: str, index: int = 0) -> Dict[str, Any]:
        """Execute the scraping process for a single URL."""
        try:
            logger.info(f"Scraping URL: {url}")
            
            # Check for duplicates
            existing = self.state_manager.get_by_source_url(url)
            if existing:
                logger.info(f"URL already scraped: {url} (ID: {existing.id})")
                return {"status": "skipped", "reason": "duplicate_url", "id": existing.id}
            
            # Generate mock transcript (replace with real scraping later)
            result = generate_test_transcript(index)
            
            # Save raw data
            file_path = save_data(result.get('id'), result, 'raw')
            
            # Create pipeline state
            scrape_cycle = datetime.now().strftime("%Y-%m-%d_%H:00:00")
            self.state_manager.create_state(
                result.get('id'), 
                scrape_cycle, 
                file_path, 
                result.get('source_url')
            )
            
            logger.info(f"Successfully scraped: {url} -> {result.get('id')}")
            return {
                "status": "success", 
                "id": result.get('id'), 
                "url": url,
                "file_path": file_path
            }
            
        except Exception as e:
            logger.error(f"Error scraping {url}: {str(e)}")
            raise
