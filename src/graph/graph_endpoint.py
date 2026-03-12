"""
Graph endpoint for loading data into Neo4j.
"""

from src.shared.base_endpoint import BaseEndpoint
from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.graph.pipeline import load_to_graph
from src.graph.models import GraphContext, GraphResult


class GraphEndpoint(BaseEndpoint):
    """Endpoint for loading data into Neo4j."""
    
    def __init__(self) -> None:
        super().__init__("GraphEndpoint")
    
    def execute(self, state: PipelineState) -> EndpointResponse:
        """Execute the Neo4j loading process for a single item."""
        processing_context = GraphContext(
            id=state.id,
            stages=state.stages,
            matched_speakers=state.matched_speakers,
            title=state.title,
            publication_date=state.publication_date,
            source_url=state.source_url,
        )

        # Execute graph loading pipeline - returns StageResult
        stage_result = load_to_graph(processing_context)

        # Parse artifact using GraphResult model
        graph_result = GraphResult.model_validate(stage_result.artifact)

        self.logger.debug(
            f"Successfully loaded item {state.id} to Neo4j - {graph_result.data.nodes_created} nodes, {graph_result.data.relationships_created} relationships"
        )

        return self._success(stage_result, PipelineStages.GRAPH)
