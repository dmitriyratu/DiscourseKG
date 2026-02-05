"""Configuration for graph preprocessing and Neo4j loading."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class GraphConfig(BaseModel):
    """Configuration settings for graph preprocessing and Neo4j."""
    # Sentiment aggregation
    DECIMAL_PRECISION: int = Field(default=3, description="Number of decimal places for sentiment proportions")
    
    # Neo4j connection
    NEO4J_URI: Optional[str] = Field(default_factory=lambda: os.getenv("NEO4J_URI"))
    NEO4J_USER: Optional[str] = Field(default_factory=lambda: os.getenv("NEO4J_USER"))
    NEO4J_PASSWORD: Optional[str] = Field(default_factory=lambda: os.getenv("NEO4J_PASSWORD"))
    NEO4J_DATABASE: Optional[str] = Field(default_factory=lambda: os.getenv("NEO4J_DATABASE"))
    
    # Neo4j batch settings
    BATCH_SIZE: int = Field(default=100)
    
    model_config = {"frozen": True}  # Make immutable


graph_config = GraphConfig()

