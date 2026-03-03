"""Data models for filter domain."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from src.shared.models import ContentType, StageOperationResult


class LLMFilterOutput(BaseModel):
    """LLM structured output — only what the model returns."""
    content_type: ContentType = Field(
        ...,
        description="from CONTENT TYPE options above: {content_type_options}"
    )
    active_speakers: List[str] = Field(..., description="All active contributors found in content")
    reason: str = Field(..., description="Brief explanation of who is speaking and why")


class FilterOutput(BaseModel):
    """Full filter result with computed fields."""
    content_type: ContentType = Field(..., description="from CONTENT TYPE options above: {content_type_options}")
    active_speakers: List[str] = Field(..., description="All active contributors found in content")
    matched_speakers: Dict[str, str] = Field(..., description="Matched speakers: id -> display_name")
    is_relevant: bool = Field(..., description="Whether any tracked speaker is an active contributor")
    reason: str = Field(..., description="Brief explanation of the filtering decision")


class FilterContext(BaseModel):
    """Processing context for filter operation."""
    id: str = Field(..., description="Unique identifier for the item")
    title: str = Field(..., description="Article title")
    content: str = Field(..., description="Scrape text")
    tracked_speaker_hints: List[str] = Field(..., description="Display names from speakers.json for normalization")
    display_name_to_id: Dict[str, str] = Field(..., description="Display name -> speaker id for mapping matches")


class FilterStageMetadata(BaseModel):
    """Metadata stored in pipeline state for filter stage."""
    content_type: Optional[ContentType] = Field(None, description="from CONTENT TYPE options above: {content_type_options}")
    model_used: str = Field(..., description="LLM model used for filtering")
    input_tokens: int = Field(default=0, description="Input tokens used")
    output_tokens: int = Field(default=0, description="Output tokens used")
    matched_speakers: Dict[str, str] = Field(default_factory=dict, description="Matched speakers: id -> display_name")


class FilterResult(StageOperationResult[FilterOutput]):
    """Result of filter operation."""
    pass
