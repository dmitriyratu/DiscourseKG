"""
Scrape endpoint for collecting speaker transcripts.
"""

from typing import Dict, Any
from src.shared.base_endpoint import BaseEndpoint
from tests.test_transcript_generator import generate_test_transcript
from src.pipeline_config import PipelineStages


class ScrapeEndpoint(BaseEndpoint):
    """Endpoint for scraping speaker transcripts."""
    
    def __init__(self):
        super().__init__("ScrapeEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the scraping process for a single item."""
        try:
            url = item['url']
            speaker = item['speaker']
            index = item.get('index', 0)
            
            self.logger.info(f"Scraping URL: {url}")
            
            # Generate mock transcript (replace with real scraping later)
            # Use different content types for variety: speech, interview, debate
            content_types = ["speech", "interview", "debate"]
            content_type = content_types[index % len(content_types)]
            result = generate_test_transcript(index, content_type)
            
            # Calculate word count from transcript
            transcript = result.get('transcript', '')
            word_count = len(transcript.split()) if transcript else 0
            result['word_count'] = word_count
            
            self.logger.info(f"Successfully scraped: {url} -> {result.get('id')} ({word_count} words)")
            
            return self._create_success_response(
                id=result.get('id'),
                result=result,
                stage=PipelineStages.SCRAPE
            )
            
        except Exception as e:
            id = item.get('id', 'unknown')
            self.logger.error(f"Error scraping {item.get('url', 'unknown')}: {str(e)}")
            return self._create_error_response(
                id=id,
                stage=PipelineStages.SCRAPE,
                error=str(e)
            )
