"""Data models for Neo4j graph loading."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from src.shared.pipeline_definitions import StageOperationResult


class SpeakerNode(BaseModel):
    """Speaker data for Neo4j node creation."""
    speaker_id: str
    name: str
    role: str = ""
    organization: str = ""
    industry: str = ""
    region: str = ""


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


class EntityInTopic(BaseModel):
    """Entity discussed within a topic context, with its claims."""
    entity_name: str
    entity_type: str
    claims: List[Dict[str, Any]]


class TopicGroup(BaseModel):
    """A topic category discussed in a communication, grouping multiple entities."""
    topic_id: str = Field(..., description="Unique ID: {comm_id}__{speaker}__{topic}")
    topic: str
    speaker: str
    topic_summary: str
    entities: List[EntityInTopic]


class AssembledGraphData(BaseModel):
    """Assembled data ready for Neo4j loading."""
    id: str = Field(..., description="Communication ID")
    speakers: List[SpeakerNode] = Field(..., description="Speaker nodes to create")
    communication: CommunicationData = Field(..., description="Communication metadata")
    topics: List[TopicGroup] = Field(..., description="Topic groups each containing entities and claims")


class GraphLoadStats(BaseModel):
    """Graph loading statistics (nodes and relationships created in Neo4j)."""
    nodes_created: int = Field(default=0, description="Number of nodes created in Neo4j")
    relationships_created: int = Field(default=0, description="Number of relationships created in Neo4j")


class GraphResult(StageOperationResult[GraphLoadStats]):
    """Result of graph loading operation (artifact only, no metadata)."""
    pass


class GraphContext(BaseModel):
    """Processing context for graph loading operation."""
    id: str = Field(..., description="Unique identifier for the item")
    stage_outputs: Dict[str, Any] = Field(default_factory=dict, description="Per-stage metadata with file paths")
    matched_speakers: List[str] = Field(default_factory=list, description="Matched speakers (display names)")
    title: Optional[str] = Field(None, description="Article title")
    publication_date: Optional[str] = Field(None, description="Publication date (YYYY-MM-DD)")
    source_url: Optional[str] = Field(None, description="Article URL")