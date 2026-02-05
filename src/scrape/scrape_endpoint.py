"""
Scrape endpoint for collecting speaker transcripts.
"""

from typing import Dict, Any
from src.shared.base_endpoint import BaseEndpoint
from src.scrape.pipeline import scrape_content
from src.shared.pipeline_definitions import PipelineStages
from src.scrape.models import ScrapeItem, ScrapeContext


class ScrapeEndpoint(BaseEndpoint):
    """Endpoint for scraping speaker transcripts."""
    
    def __init__(self):
        super().__init__("ScrapeEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the scraping process for a single item."""
        scrape_item = ScrapeItem(**item)
        
        # Validate required fields
        if not scrape_item.source_url:
            raise ValueError(f"Missing source_url for item {scrape_item.id}")
        
        # Build processing context
        processing_context = ScrapeContext(
            id=scrape_item.id,
            source_url=scrape_item.source_url
        )

        # Execute scraping pipeline - returns StageResult
        stage_result = scrape_content(processing_context)

        
        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.SCRAPE.value,
            state_update=stage_result.metadata
        )
