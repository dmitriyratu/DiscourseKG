"""Data models for summarization domain."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class SummarizationData(BaseModel):
    """Summarized content data."""
    summarize: str = Field(..., description="The summarized text")
    original_word_count: int = Field(..., description="Word count of original text")
    summary_word_count: int = Field(..., description="Word count of summary")
    compression_ratio: float = Field(..., description="Ratio of summary length to original length")
    target_word_count: int = Field(..., description="Target word count for summary")


class SummarizationResult(BaseModel):
    """Result of summarization operation (artifact only, no metadata)."""
    id: str = Field(..., description="Unique identifier for the summarized content")
    success: bool = Field(..., description="Whether summarization was successful")
    data: Optional[SummarizationData] = Field(None, description="Summarized content data")
    error_message: Optional[str] = Field(None, description="Error message if summarization failed")


class SummarizeItem(BaseModel):
    """Input record required for summarization."""

    id: str = Field(..., description="Identifier of the pipeline item to summarize")
    file_paths: Dict[str, str] = Field(default_factory=dict, description="Completed stage artifacts")
    latest_completed_stage: str = Field(..., description="Last stage completed for this item")


class SummarizeContext(BaseModel):
    """Processing context for summarization operation."""
    id: str = Field(..., description="Unique identifier for the item")
    text: str = Field(..., description="Text content to summarize")
    target_tokens: int = Field(..., description="Target token count for summary")