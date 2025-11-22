"""
Graph endpoint for loading data into Neo4j.
"""

from typing import Dict, Any

from src.shared.base_endpoint import BaseEndpoint
from src.graph.pipeline import load_to_graph
from src.shared.pipeline_definitions import PipelineStages
from src.graph.models import GraphItem, GraphContext


class GraphEndpoint(BaseEndpoint):
    """Endpoint for loading data into Neo4j."""
    
    def __init__(self):
        super().__init__("GraphEndpoint")
    
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Neo4j loading process for a single item."""
        graph_item = GraphItem(**item)

        # Build processing context
        processing_context = GraphContext(
            id=graph_item.id,
            file_paths=graph_item.file_paths,
            speaker=graph_item.speaker
        )

        # Execute graph loading pipeline - returns StageResult
        stage_result = load_to_graph(processing_context)

        self.logger.debug(
            f"Successfully loaded item {graph_item.id} to Neo4j - {stage_result.artifact['data']['nodes_created']} nodes, {stage_result.artifact['data']['relationships_created']} relationships"
        )

        return self._create_success_response(
            result=stage_result.artifact,
            stage=PipelineStages.GRAPH.value,
            state_update=stage_result.metadata
        )
