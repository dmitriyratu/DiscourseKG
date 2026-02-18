"""
Grapher for assembling and loading data into Neo4j.

Orchestrates data assembly and Neo4j ingestion.
"""

from typing import Any

from neo4j import GraphDatabase

from src.graph.config import graph_config
from src.graph.data_assembler import GraphDataAssembler
from src.graph.models import GraphContext, GraphData, GraphResult
from src.graph.neo4j_loader import Neo4jLoader
from src.shared.pipeline_definitions import StageResult
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Grapher:
    """
    Grapher implementation for loading data into Neo4j knowledge graph.

    Delegates data assembly to GraphDataAssembler and Neo4j writes to Neo4jLoader.
    """

    def __init__(self) -> None:
        self.data_assembler = GraphDataAssembler()
        self.driver: Any = None
        logger.debug("Grapher initialized")

    def __enter__(self) -> "Grapher":
        """Context manager entry - establish Neo4j connection."""
        self.driver = GraphDatabase.driver(
            graph_config.NEO4J_URI,
            auth=(graph_config.NEO4J_USER, graph_config.NEO4J_PASSWORD),
        )
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - close Neo4j connection."""
        if self.driver:
            self.driver.close()

    def load_graph(self, processing_context: GraphContext) -> StageResult:
        """Load data into Neo4j from processing context."""
        id = processing_context.id
        logger.debug(f"Starting graph loading for {id}")

        data = self.data_assembler.assemble(processing_context)

        loader = Neo4jLoader(self.driver)
        stats = loader.load(data)

        return self._create_result(id, stats)

    def _create_result(self, id: str, stats: dict) -> StageResult:
        """Create StageResult with separated artifact and metadata."""
        graph_data = GraphData(
            nodes_created=stats["nodes_created"],
            relationships_created=stats["relationships_created"],
        )
        artifact = GraphResult(
            id=id,
            success=True,
            data=graph_data,
            error_message=None,
        )
        metadata = {}

        logger.debug(
            f"Successfully loaded {id} to Neo4j: {graph_data.nodes_created} nodes, "
            f"{graph_data.relationships_created} relationships"
        )

        return StageResult(artifact=artifact.model_dump(), metadata=metadata)
