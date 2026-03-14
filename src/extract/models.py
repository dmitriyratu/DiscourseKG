"""Data models for extraction domain."""

from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from src.shared.pipeline_definitions import StageOperationResult


class Passage(BaseModel):
    """A single passage about an entity from a tracked speaker."""
    model_config = ConfigDict(extra="forbid")
    verbatim: str = Field(..., description="Full surrounding exchange from the transcript with [Speaker] markers, including the question/context that prompted the response")


class EntityAttribution(BaseModel):
    """A single entity attributed to a speaker with reasoning."""
    model_config = ConfigDict(extra="forbid")
    name: str = Field(..., description="Canonical entity name")
    reason: str = Field(..., description="One sentence: why this entity qualifies — what substantive claim the speaker makes about it")


class SpeakerEntities(BaseModel):
    """Single speaker with their attributed entities."""
    speaker: str = Field(..., description="Tracked speaker name")
    entities: List[EntityAttribution] = Field(..., description="Entities this speaker substantively discusses, each with a reason")


class SpeakerEntityMap(BaseModel):
    """Phase 1 output: per-speaker entity attribution."""
    speakers: List[SpeakerEntities] = Field(..., description="List of tracked speakers and their entities")


EntityWhitelist = Dict[str, Dict[str, str]]  # speaker → {entity_name → reason}


class ExtractionStats(BaseModel):
    """Summary statistics for an extraction run."""
    entities_attributed: int = Field(..., description="Phase 1: total entities attributed across all speakers")
    entities_extracted: int = Field(..., description="Phase 2: entities with at least one passage")
    passages_by_speaker: Dict[str, int] = Field(..., description="Total passage count per speaker")


class ExtractionOutput(BaseModel):
    """Output schema for entity extraction."""
    by_speaker: Dict[str, Dict[str, List[Passage]]] = Field(
        default_factory=dict,
        description="Speaker → entity → passages (verbatim transcript exchanges)",
    )
    entity_whitelist: EntityWhitelist = Field(
        default_factory=dict,
        description="Phase 1 output: speaker → entity name → reason",
    )
    stats: ExtractionStats = Field(
        default=None,
        description="Summary statistics for this extraction run",
    )


class ExtractContext(BaseModel):
    """Processing context for extraction operation."""
    id: str = Field(..., description="Unique identifier for the item")
    content: str = Field(..., description="Full text to extract entities from")
    content_type: str = Field(default="unknown", description="Content type from filter stage (e.g. interview, speech)")
    matched_speakers: List[str] = Field(default_factory=list, description="Tracked speakers to extract passages for (from filter stage)")


class ExtractStageMetadata(BaseModel):
    """Metadata stored in pipeline state for extract stage."""
    model_used: str = Field(..., description="LLM model used for extraction")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")


class ExtractionResult(StageOperationResult[ExtractionOutput]):
    """Result of extraction operation."""
    pass
