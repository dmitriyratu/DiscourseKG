"""
Graph loading pipeline component for DiscourseKG platform.

Loads preprocessed data directly into Neo4j.
"""

from typing import Dict, Any
from src.graph.loader import Neo4jLoader


def load_to_graph(processing_context: Dict[str, Any]) -> Dict[str, Any]:
    """Load preprocessed data into Neo4j knowledge graph."""
    with Neo4jLoader() as loader:
        return loader.load_to_neo4j(processing_context)

