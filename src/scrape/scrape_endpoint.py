"""
Scrape endpoint for collecting speaker transcripts.
"""

from typing import Dict, Any
from src.shared.base_endpoint import BaseEndpoint
from src.scrape.pipeline import scrape_content
from src.pipeline_config import PipelineStages


class ScrapeEndpoint(BaseEndpoint):
    """Endpoint for scraping speaker transcripts."""
    
    def __init__(self):
        super().__init__("ScrapeEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the scraping process for a single item."""
        try:
            url = item['source_url']
            self.logger.info(f"Processing scrape request for URL: {url}")
            
            # Process through scraping pipeline
            result = scrape_content(item)
            
            # Calculate word count
            scrape = result.get('scrape', '')
            word_count = len(scrape.split()) if scrape else 0
            result['word_count'] = word_count
            
            self.logger.debug(f"Successfully scraped: {url} -> {result.get('id')} ({word_count} words)")
            
            return self._create_success_response(
                id=result.get('id'),
                result=result,
                stage=PipelineStages.SCRAPE.value
            )
            
        except Exception as e:
            id = item.get('id', 'unknown')
            self.logger.error(f"Error scraping {item.get('source_url', 'unknown')}: {str(e)}")
            # Let exception bubble up to flow processor
            raise
