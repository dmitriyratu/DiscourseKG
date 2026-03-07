"""Data models for Neo4j graph loading."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from src.shared.models import StageOperationResult


class SpeakerNode(BaseModel):
    """Speaker data for Neo4j node creation."""
    name_id: str = Field(..., description="Speaker ID from matched_speakers")
    name: str = Field(..., description="Display name")
    display_name: str = Field(..., description="Display name")
    role: str = Field(default="", description="Speaker role")
    organization: str = Field(default="", description="Organization")
    industry: str = Field(default="", description="Industry")
    region: str = Field(default="", description="Region")


class CommunicationData(BaseModel):
    """Communication metadata for Neo4j loading."""
    id: str = Field(..., description="Communication ID")
    title: str = Field(..., description="Article title")
    content_type: str = Field(..., description="Content type enum value")
    content_date: str = Field(..., description="Publication date")
    source_url: str = Field(default="", description="Source URL")
    full_text: str = Field(default="", description="Full scraped text")
    word_count: int = Field(default=0, description="Word count")
    was_summarized: bool = Field(default=False, description="Whether content was summarized")
    compression_ratio: float = Field(default=1.0, description="Compression ratio if summarized")


class AssembledGraphData(BaseModel):
    """Assembled data ready for Neo4j loading."""
    id: str = Field(..., description="Communication ID")
    speakers: List[SpeakerNode] = Field(..., description="Speaker nodes to create")
    communication: CommunicationData = Field(..., description="Communication metadata")
    entities: List[Dict[str, Any]] = Field(..., description="Preprocessed entities with aggregated sentiment")


class GraphData(BaseModel):
    """Graph loading statistics (nodes and relationships created in Neo4j)."""
    nodes_created: int = Field(default=0, description="Number of nodes created in Neo4j")
    relationships_created: int = Field(default=0, description="Number of relationships created in Neo4j")


class GraphResult(StageOperationResult[GraphData]):
    """Result of graph loading operation (artifact only, no metadata)."""
    pass


class GraphContext(BaseModel):
    """Processing context for graph loading operation."""
    id: str = Field(..., description="Unique identifier for the item")
    stages: Dict[str, Any] = Field(default_factory=dict, description="Per-stage metadata")
    matched_speakers: Dict[str, str] = Field(default_factory=dict, description="Matched speakers: id -> display_name")
    title: Optional[str] = Field(None, description="Article title")
    publication_date: Optional[str] = Field(None, description="Publication date (YYYY-MM-DD)")
    source_url: Optional[str] = Field(None, description="Article URL")


class GraphItem(BaseModel):
    """Input record required for graph loading."""
    id: str = Field(..., description="Identifier of the pipeline item to load")
    stages: Dict[str, Any] = Field(default_factory=dict, description="Per-stage metadata")
    matched_speakers: Dict[str, str] = Field(default_factory=dict, description="Matched speakers: id -> display_name")