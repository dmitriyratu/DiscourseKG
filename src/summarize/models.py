"""Data models for summarization domain."""

from pydantic import BaseModel, Field
from typing import Optional
from src.shared.pipeline_definitions import StageOperationResult


class SummarizeStageMetadata(BaseModel):
    """Metadata stored in pipeline state for summarize stage."""
    compression_of_original: float = Field(..., description="Ratio of summary to original (1 = no compression)")


class SummarizationData(BaseModel):
    """Summarized content data. When compression_of_original=1, summarize is null (use scrape)."""
    summarize: Optional[str] = Field(None, description="The summarized text (null when no compression)")
    compression_of_original: float = Field(..., description="Ratio of summary length to original (1 = no compression)")
    original_word_count: Optional[int] = Field(None, description="Word count of original (omitted when no compression)")
    summary_word_count: Optional[int] = Field(None, description="Word count of summary (omitted when no compression)")


class SummarizationResult(StageOperationResult[SummarizationData]):
    """Result of summarization operation (artifact only, no metadata)."""
    pass


class SummarizeContext(BaseModel):
    """Processing context for summarization operation."""
    id: str = Field(..., description="Unique identifier for the item")
    text: str = Field(..., description="Text content to summarize")
    target_tokens: int = Field(..., description="Target token count for summary")