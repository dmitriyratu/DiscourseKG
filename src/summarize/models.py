"""Data models for summarization domain."""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from src.shared.models import StageOperationResult


class SummarizationData(BaseModel):
    """Summarized content data. When compression_of_original=1, summarize is null (use scrape)."""
    summarize: Optional[str] = Field(None, description="The summarized text (null when no compression)")
    compression_of_original: float = Field(..., description="Ratio of summary length to original (1 = no compression)")
    original_word_count: Optional[int] = Field(None, description="Word count of original (omitted when no compression)")
    summary_word_count: Optional[int] = Field(None, description="Word count of summary (omitted when no compression)")


class SummarizationResult(StageOperationResult[SummarizationData]):
    """Result of summarization operation (artifact only, no metadata)."""
    pass


class SummarizeItem(BaseModel):
    """Input record required for summarization."""
    id: str = Field(..., description="Identifier of the pipeline item to summarize")
    latest_completed_stage: str = Field(..., description="Last stage completed for this item")
    stages: Dict[str, Any] = Field(default_factory=dict, description="Per-stage metadata")
    
    def get_current_file_path(self) -> Optional[str]:
        """Get file path for the latest completed stage"""
        if self.latest_completed_stage and self.latest_completed_stage in self.stages:
            return self.stages[self.latest_completed_stage].get('file_path')
        return None


class SummarizeContext(BaseModel):
    """Processing context for summarization operation."""
    id: str = Field(..., description="Unique identifier for the item")
    text: str = Field(..., description="Text content to summarize")
    target_tokens: int = Field(..., description="Target token count for summary")