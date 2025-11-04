"""Data models for Neo4j graph loading."""

from pydantic import BaseModel, Field
from typing import Optional


class Neo4jLoadResult(BaseModel):
    """Result of Neo4j loading operation with statistics."""
    id: str = Field(..., description="Unique identifier for the content")
    success: bool = Field(..., description="Whether Neo4j loading was successful")
    nodes_created: Optional[int] = Field(None, description="Number of nodes created in Neo4j")
    relationships_created: Optional[int] = Field(None, description="Number of relationships created in Neo4j")
    error_message: Optional[str] = Field(None, description="Error message if loading failed")

