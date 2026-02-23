"""
Discover endpoint for finding content sources.

This endpoint handles the discovery of content sources and creation of pipeline states
using autonomous web scraping.
"""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.pipeline_definitions import EndpointResponse
from src.discover.pipeline import discover_content
from src.shared.pipeline_definitions import PipelineStages
from src.discover.models import DiscoveryRequest


class DiscoverEndpoint(BaseEndpoint):
    """Endpoint for discovering content sources."""
    
    def __init__(self) -> None:
        super().__init__("DiscoverEndpoint")
    
    def execute(self, discovery_params: DiscoveryRequest) -> EndpointResponse:
        """Execute the discovery process for given parameters."""
        self.logger.info(f"Processing discovery request: {discovery_params.start_date} to {discovery_params.end_date}")
        self.logger.debug(f"Discovery parameters: {len(discovery_params.search_urls)} search URLs")
        
        stage_result = discover_content(discovery_params)
        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.DISCOVER.value,
            state_update=stage_result.metadata
        )
