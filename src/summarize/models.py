"""Data models for summarization domain."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from src.shared.models import StageOperationResult


class SummarizationData(BaseModel):
    """Summarized content data."""
    summarize: str = Field(..., description="The summarized text")
    original_word_count: int = Field(..., description="Word count of original text")
    summary_word_count: int = Field(..., description="Word count of summary")
    compression_ratio: float = Field(..., description="Ratio of summary length to original length")
    target_word_count: int = Field(..., description="Target word count for summary")


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