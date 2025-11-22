"""Data models for Neo4j graph loading."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class GraphData(BaseModel):
    """Graph loading data with Neo4j statistics."""
    nodes_created: int = Field(..., description="Number of nodes created in Neo4j")
    relationships_created: int = Field(..., description="Number of relationships created in Neo4j")


class GraphResult(BaseModel):
    """Result of graph loading operation (artifact only, no metadata)."""
    id: str = Field(..., description="Unique identifier for the content")
    success: bool = Field(..., description="Whether graph loading was successful")
    data: Optional[GraphData] = Field(None, description="Graph loading statistics")
    error_message: Optional[str] = Field(None, description="Error message if loading failed")


class GraphContext(BaseModel):
    """Processing context for graph loading operation."""
    id: str = Field(..., description="Unique identifier for the item")
    file_paths: Dict[str, str] = Field(..., description="Paths to completed stage artifacts")
    speaker: str = Field(..., description="Speaker name for loading from speakers.json")


class GraphItem(BaseModel):
    """Input record required for graph loading."""
    id: str = Field(..., description="Identifier of the pipeline item to load")
    file_paths: Dict[str, str] = Field(default_factory=dict, description="Completed stage artifacts")
    speaker: str = Field(..., description="Speaker name for the communication")