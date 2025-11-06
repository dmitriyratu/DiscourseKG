"""
Graph endpoint for loading data into Neo4j.
"""

from typing import Dict, Any

from src.shared.base_endpoint import BaseEndpoint
from src.graph.pipeline import load_to_graph
from src.pipeline_config import PipelineStages


class GraphEndpoint(BaseEndpoint):
    """Endpoint for loading data into Neo4j."""
    
    def __init__(self):
        super().__init__("GraphEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Neo4j loading process for a single item."""
        try:
            # Create processing context (immutable)
            processing_context = {
                'id': item['id'],
                'file_paths': item.get('file_paths', {}),
            }
            
            # Process through graph loading pipeline
            result = load_to_graph(processing_context)
            
            self.logger.debug(f"Successfully loaded item {item['id']} to Neo4j - {result['data']['nodes_created']} nodes, {result['data']['relationships_created']} relationships")
            
            return self._create_success_response(
                result=result,
                stage=PipelineStages.GRAPH.value
            )
            
        except Exception as e:
            raise
