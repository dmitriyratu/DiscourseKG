"""Data models for Neo4j graph loading."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GraphData(BaseModel):
    """Graph loading data with Neo4j statistics."""
    nodes_created: int = Field(..., description="Number of nodes created in Neo4j")
    relationships_created: int = Field(..., description="Number of relationships created in Neo4j")


class GraphResult(BaseModel):
    """Result of graph loading operation."""
    id: str = Field(..., description="Unique identifier for the content")
    success: bool = Field(..., description="Whether graph loading was successful")
    data: Optional[GraphData] = Field(None, description="Graph loading statistics")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error_message: Optional[str] = Field(None, description="Error message if loading failed")

