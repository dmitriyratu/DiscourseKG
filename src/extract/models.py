"""Data models for extraction domain."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.shared.models import StageOperationResult


class EntityListOutput(BaseModel):
    """Phase 1 output: canonical entity names only."""
    entities: List[str] = Field(description="Canonical entity names")


class ExtractedEntity(BaseModel):
    """Single entity with its passages from the LLM."""
    entity_name: str = Field(..., min_length=1, max_length=200, description="Canonical entity name")
    passages: List[str] = Field(..., min_items=1, description="Passages where entity is discussed, with speaker markers (canonical name in brackets)")


class ExtractionOutput(BaseModel):
    """Output schema for entity extraction."""
    entities: List[ExtractedEntity] = Field(description="Extracted entities with passages")
    entity_whitelist: List[str] = Field(
        default_factory=list,
        description="Entity whitelist from Phase 1 (after speaker filtering)",
    )


class ExtractContext(BaseModel):
    """Processing context for extraction operation."""
    id: str = Field(..., description="Unique identifier for the item")
    content: str = Field(..., description="Full text to extract entities from")
    active_speakers: List[str] = Field(default_factory=list, description="Speaker names to exclude from entities (from filter stage)")
    previous_error: Optional[str] = Field(None, description="Previous error message if retrying")
    previous_failed_output: Optional[str] = Field(None, description="Previous failed output if retrying")


class ExtractStageMetadata(BaseModel):
    """Metadata stored in pipeline state for extract stage."""
    model_used: str = Field(..., description="LLM model used for extraction")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")


class ExtractionResult(StageOperationResult[ExtractionOutput]):
    """Result of extraction operation."""
    pass


class ExtractItem(BaseModel):
    """Input record required for extraction."""
    id: str = Field(..., description="Identifier of the pipeline item to extract")
    latest_completed_stage: str = Field(..., description="Last stage completed for this item")
    stages: Dict[str, Any] = Field(default_factory=dict, description="Per-stage metadata")
    error_message: Optional[str] = Field(None, description="Previous error message if extraction is a retry")
