"""Configuration for graph preprocessing and Neo4j loading."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class GraphConfig:
    """Configuration settings for graph preprocessing and Neo4j."""
    # Sentiment aggregation
    DECIMAL_PRECISION: int = 3  # Number of decimal places for sentiment proportions
    
    # Neo4j connection
    NEO4J_URI: str = os.getenv("NEO4J_URI", "neo4j://localhost:7687")
    NEO4J_USER: str = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD: str = os.getenv("NEO4J_PASSWORD", "")
    NEO4J_DATABASE: str = os.getenv("NEO4J_DATABASE", "neo4j")
    
    # Neo4j batch settings
    BATCH_SIZE: int = 100


graph_config = GraphConfig()

