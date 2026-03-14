"""Data models for Neo4j graph loading."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

from src.shared.pipeline_definitions import StageOperationResult


class SpeakerNode(BaseModel):
    """Speaker data for Neo4j node creation."""
    speaker_id: str = Field(..., description="Unique speaker identifier (display name)")
    name: str = Field(..., description="Display name")
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


class EntityInTopic(BaseModel):
    """Entity discussed within a topic context, with its claims."""
    entity_name: str = Field(..., description="Canonical entity name")
    entity_type: str = Field(..., description="Entity type")
    claims: List[Dict[str, Any]] = Field(..., description="Claims made about this entity")


class TopicGroup(BaseModel):
    """A topic category discussed in a communication, grouping multiple entities."""
    topic_id: str = Field(..., description="Unique ID: {comm_id}__{speaker}__{topic}")
    topic: str = Field(..., description="Topic category")
    speaker: str = Field(..., description="Speaker display name")
    topic_summary: str = Field(..., description="LLM-generated synthesis across all entities in this topic")
    entities: List[EntityInTopic] = Field(..., description="Entities discussed under this topic")


class AssembledGraphData(BaseModel):
    """Assembled data ready for Neo4j loading."""
    id: str = Field(..., description="Communication ID")
    speakers: List[SpeakerNode] = Field(..., description="Speaker nodes to create")
    communication: CommunicationData = Field(..., description="Communication metadata")
    topics: List[TopicGroup] = Field(..., description="Topic groups each containing entities and claims")


class GraphLoadStats(BaseModel):
    """Graph loading statistics (nodes and relationships created in Neo4j)."""
    nodes_created: int = Field(default=0, description="Number of nodes created")
    relationships_created: int = Field(default=0, description="Number of relationships created")


class GraphResult(StageOperationResult[GraphLoadStats]):
    """Result of graph loading operation (artifact only, no metadata)."""
    pass


class GraphContext(BaseModel):
    """Processing context for graph loading operation."""
    id: str = Field(..., description="Communication ID")
    stage_outputs: Dict[str, Any] = Field(default_factory=dict, description="Per-stage metadata with file paths")
    matched_speakers: List[str] = Field(default_factory=list, description="Matched speakers (display names)")
    title: Optional[str] = Field(default=None, description="Article title")
    publication_date: Optional[str] = Field(default=None, description="Publication date (YYYY-MM-DD)")
    source_url: Optional[str] = Field(default=None, description="Source URL")
