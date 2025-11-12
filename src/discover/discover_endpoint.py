"""
Discover endpoint for finding content sources.

This endpoint handles the discovery of content sources and creation of pipeline states.
Currently uses mock discovery - will be replaced with agent-based discovery.
"""

from typing import Dict, Any, List
from src.shared.base_endpoint import BaseEndpoint
from src.discover.pipeline import discover_content
from src.shared.pipeline_definitions import PipelineStages
from src.discover.models import DiscoveryRequest


class DiscoverEndpoint(BaseEndpoint):
    """Endpoint for discovering content sources."""
    
    def __init__(self):
        super().__init__("DiscoverEndpoint")
    
    def execute(self, discovery_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the discovery process for given parameters."""
        request = DiscoveryRequest(**discovery_params)
        
        self.logger.info(f"Processing discovery request for speaker: {request.speaker}")
        self.logger.debug(f"Discovery parameters: {request.start_date} to {request.end_date}")
        
        # Execute discovery pipeline - returns StageResult
        stage_result = discover_content(request.model_dump())
        
        self.logger.debug(
            f"Successfully discovered {stage_result.artifact['data']['item_count']} items for speaker {request.speaker}"
        )
        
        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.DISCOVER.value,
            state_update=stage_result.metadata
        )