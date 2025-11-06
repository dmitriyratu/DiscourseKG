"""
Graph loading pipeline component for DiscourseKG platform.

Loads preprocessed data directly into Neo4j.
"""

from typing import Dict, Any
from src.graph.grapher import Grapher


def load_to_graph(processing_context: Dict[str, Any]) -> Dict[str, Any]:
    """Load preprocessed data into Neo4j knowledge graph."""
    return Grapher().load_graph(processing_context)

