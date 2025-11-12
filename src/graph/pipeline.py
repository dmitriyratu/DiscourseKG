"""
Graph loading pipeline component for DiscourseKG platform.

Loads preprocessed data directly into Neo4j.
"""

from src.graph.grapher import Grapher
from src.graph.models import GraphContext
from src.shared.pipeline_definitions import StageResult


def load_to_graph(processing_context: GraphContext) -> StageResult:
    """Load preprocessed data into Neo4j knowledge graph."""
    return Grapher().load_graph(processing_context)

