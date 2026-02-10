"""
Scrape endpoint for collecting speaker transcripts.
"""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.pipeline_definitions import EndpointResponse
from src.scrape.pipeline import scrape_content
from src.shared.pipeline_definitions import PipelineStages, PipelineState
from src.scrape.models import ScrapeContext


class ScrapeEndpoint(BaseEndpoint):
    """Endpoint for scraping speaker transcripts."""
    
    def __init__(self) -> None:
        super().__init__("ScrapeEndpoint")
    
    def execute(self, state: PipelineState) -> EndpointResponse:
        """Execute the scraping process for a single item."""
        # Validate required fields
        if not state.source_url:
            raise ValueError(f"Missing source_url for item {state.id}")
        
        # Build processing context
        processing_context = ScrapeContext(
            id=state.id,
            source_url=state.source_url
        )

        # Execute scraping pipeline - returns StageResult
        stage_result = scrape_content(processing_context)

        
        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.SCRAPE.value,
            state_update=stage_result.metadata
        )
