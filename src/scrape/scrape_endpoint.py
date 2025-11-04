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
            
            # Create processing context (immutable)
            processing_context = {
                'id': item['id'],
                'source_url': item['source_url'],
                'content_type': item.get('content_type'),
                'metadata': {
                    'title': item.get('title'),
                    'content_date': item.get('content_date'),
                    'speaker': item.get('speaker')
                }
            }
            
            # Process through scraping pipeline
            result = scrape_content(processing_context)
            
            # Calculate word count
            scrape = result.get('data', {}).get(PipelineStages.SCRAPE.value, '')
            word_count = len(scrape.split()) if scrape else 0
            result['word_count'] = word_count
            
            return self._create_success_response(
                id=result.get('id'),
                result=result,
                stage=PipelineStages.SCRAPE.value
            )
            
        except Exception as e:
            
            raise
