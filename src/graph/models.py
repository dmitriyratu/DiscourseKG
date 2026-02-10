"""Data models for Neo4j graph loading."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from src.shared.models import StageOperationResult


class GraphData(BaseModel):
    """Graph loading data with Neo4j statistics."""
    nodes_created: int = Field(..., description="Number of nodes created in Neo4j")
    relationships_created: int = Field(..., description="Number of relationships created in Neo4j")


class GraphResult(StageOperationResult[GraphData]):
    """Result of graph loading operation (artifact only, no metadata)."""
    pass


class GraphContext(BaseModel):
    """Processing context for graph loading operation."""
    id: str = Field(..., description="Unique identifier for the item")
    stages: Dict[str, Any] = Field(default_factory=dict, description="Per-stage metadata")
    speaker: str = Field(..., description="Speaker name for loading from speakers.json")
    title: Optional[str] = Field(None, description="Article title")
    publication_date: Optional[str] = Field(None, description="Publication date (YYYY-MM-DD)")


class GraphItem(BaseModel):
    """Input record required for graph loading."""
    id: str = Field(..., description="Identifier of the pipeline item to load")
    stages: Dict[str, Any] = Field(default_factory=dict, description="Per-stage metadata")
    speaker: str = Field(..., description="Speaker name for the communication")