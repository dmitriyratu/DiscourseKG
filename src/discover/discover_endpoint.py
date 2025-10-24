"""
Discover endpoint for finding content sources.

This endpoint handles the discovery of content sources and creation of pipeline states.
Currently uses mock discovery - will be replaced with agent-based discovery.
"""

from typing import Dict, Any, List
from src.shared.base_endpoint import BaseEndpoint
from src.discover.pipeline import discover_content
from src.pipeline_config import PipelineStages


class DiscoverEndpoint(BaseEndpoint):
    """Endpoint for discovering content sources."""
    
    def __init__(self):
        super().__init__("DiscoverEndpoint")
    
    def execute(self, discovery_params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the discovery process for given parameters."""
        try:
            speaker = discovery_params['speaker']
            start_date = discovery_params['start_date']
            end_date = discovery_params['end_date']
            
            self.logger.info(f"Processing discovery request for speaker: {speaker}")
            self.logger.debug(f"Discovery parameters: {start_date} to {end_date}")
            
            # Process through discovery pipeline
            result = discover_content(discovery_params)
            
            self.logger.debug(f"Successfully discovered {len(result.get('discovered_items', []))} items")
            
            return self._create_success_response(
                id=result.get('discovery_id'),
                result=result,
                stage=PipelineStages.DISCOVER.value
            )
            
        except Exception as e:
            id = discovery_params.get('id', 'unknown')
            self.logger.error(f"Error discovering content for {discovery_params.get('speaker', 'unknown')}: {str(e)}", 
                             extra={'speaker': discovery_params.get('speaker'), 'stage': PipelineStages.DISCOVER.value, 'error_type': 'endpoint_error'})
            # Let exception bubble up to flow processor
            raise
