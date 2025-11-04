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
    """Result of summarization operation with metrics and metadata."""
    id: str = Field(..., description="Unique identifier for the summarized content")
    success: bool = Field(..., description="Whether summarization was successful")
    data: Optional[SummarizationData] = Field(None, description="Summarized content data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error_message: Optional[str] = Field(None, description="Error message if summarization failed")

