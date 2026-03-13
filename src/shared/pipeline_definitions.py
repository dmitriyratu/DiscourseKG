"""
Pipeline stage definitions and flow configuration.

Used across the DiscourseKG pipeline to keep stage enums, status
constants, and shared data models centralized.
"""

from typing import Any, Dict, Generic, List, Optional, TypeVar
from enum import Enum
from pydantic import BaseModel, Field, computed_field

T = TypeVar("T")


class StageOperationResult(BaseModel, Generic[T]):
    """Base result model for all pipeline stage operations."""
    id: str = Field(..., description="Unique identifier")
    success: bool = Field(..., description="Whether operation was successful")
    data: Optional[T] = Field(None, description="Operation data if successful")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class PipelineStageStatus(str, Enum):
    """Status of a pipeline stage."""

    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    FILTERED = "FILTERED"


class PipelineStages(str, Enum):
    """Pipeline stage definitions; values match directory names and data keys."""

    DISCOVER = "discover"
    SCRAPE = "scrape"
    FILTER = "filter"
    SUMMARIZE = "summarize"
    EXTRACT = "extract"
    CATEGORIZE = "categorize"
    GRAPH = "graph"


class PipelineConfig:
    """Pipeline stage flow configuration."""

    STAGE_FLOW = {
        PipelineStages.DISCOVER: PipelineStages.SCRAPE,
        PipelineStages.SCRAPE: PipelineStages.FILTER,
        PipelineStages.FILTER: PipelineStages.SUMMARIZE,
        PipelineStages.SUMMARIZE: PipelineStages.EXTRACT,
        PipelineStages.EXTRACT: PipelineStages.CATEGORIZE,
        PipelineStages.CATEGORIZE: PipelineStages.GRAPH,
        PipelineStages.GRAPH: None,
    }

    @classmethod
    def get_next_stage(cls, current_stage: str | None, *, is_filtered: bool = False) -> Optional[str]:
        """Get the next stage after the current one. Returns None if pipeline is filtered (dead-end)."""
        if is_filtered:
            return None
        return cls.STAGE_FLOW.get(current_stage) if current_stage else None


class StageResult(BaseModel):
    """Result from a pipeline stage with separated artifact and metadata."""
    
    artifact: Dict[str, Any] = Field(..., description="Data to persist as stage output file")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata for pipeline state updates only")


class ArticleFields(BaseModel):
    """Article-level fields denormalized onto each stage row."""

    title: Optional[str] = Field(None, description="Article title")
    publication_date: Optional[str] = Field(None, description="Publication date (YYYY-MM-DD)")
    source_url: Optional[str] = Field(None, description="Article URL")
    search_url: Optional[str] = Field(None, description="Search page URL")
    run_timestamp: Optional[str] = Field(None, description="Timestamp when scraped (YYYY-MM-DD_HH:MM:SS)")
    created_at: Optional[str] = Field(None, description="ISO timestamp when record was created")


class StageMetadata(BaseModel):
    """Metadata for a specific pipeline stage."""
    completed_at: Optional[str] = Field(None, description="ISO timestamp when stage completed")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time for this stage")
    file_path: Optional[str] = Field(None, description="Output file path for this stage")
    retry_count: int = Field(default=0, description="Number of retries for this stage")
    error_message: Optional[str] = Field(None, description="Last error message if stage failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Stage-specific custom metadata")


class PipelineState(BaseModel):
    """Pipeline processing state for a single data point"""
    
    # Identity & Content (what is this?)
    id: str = Field(..., description="Unique ID from raw data")
    publication_date: Optional[str] = Field(None, description="Publication date (YYYY-MM-DD)")
    title: Optional[str] = Field(None, description="Article title")
    
    # Status (where are we?)
    latest_completed_stage: Optional[str] = Field(None, description="Latest successfully completed stage")
    next_stage: Optional[str] = Field(None, description="Next stage that needs to be processed")
    error_message: Optional[str] = Field(None, description="Error message if current stage failed")
    
    # Source (where did it come from?)
    source_url: Optional[str] = Field(None, description="Article URL (for scraping)")
    search_url: Optional[str] = Field(None, description="Search page URL (discovery source)")
    
    # Processing Info (when/how was it processed?)
    run_timestamp: str = Field(..., description="Timestamp when scraped (YYYY-MM-DD_HH:MM:SS)")
    created_at: str = Field(..., description="ISO timestamp when record was created")
    updated_at: str = Field(..., description="ISO timestamp of last update")
    processing_time_seconds: Optional[float] = Field(None, description="Total processing time across all stages")
    retry_count: int = Field(default=0, description="Total retries across all stages")
    
    # Stage-specific data (detailed breakdown)
    stages: Dict[str, StageMetadata] = Field(default_factory=dict, description="Per-stage metadata")

    def _filter_meta(self) -> Dict[str, Any]:
        return (self.stages.get("filter") or StageMetadata()).metadata

    @computed_field
    @property
    def content_type(self) -> str:
        return self._filter_meta().get("content_type") or "unknown"

    @computed_field
    @property
    def matched_speakers(self) -> List[str]:
        return self._filter_meta().get("matched_speakers") or []

    @computed_field
    @property
    def active_speakers(self) -> List[str]:
        return self._filter_meta().get("active_speakers") or []

    def get_file_path_for_stage(self, stage: str) -> Optional[str]:
        return self.stages[stage].file_path if stage in self.stages else None

    def article_fields(self) -> ArticleFields:
        """Article-level fields for denormalization onto stage rows."""
        return ArticleFields(
            title=self.title,
            publication_date=self.publication_date,
            source_url=self.source_url,
            search_url=self.search_url,
            run_timestamp=self.run_timestamp,
            created_at=self.created_at,
        )


class EndpointResponse(BaseModel):
    """Standardized response from pipeline endpoints."""
    success: bool = Field(..., description="Whether endpoint execution was successful")
    stage: str = Field(..., description="Pipeline stage name")
    output: Dict[str, Any] = Field(..., description="Stage operation result (contains StageOperationResult structure)")
    input_data: Optional[Any] = Field(None, description="Input data passed to endpoint")
    state_update: Optional[Dict[str, Any]] = Field(None, description="Metadata for pipeline state updates")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time in seconds (added by flow processor)")
    pipeline_status: Optional[PipelineStageStatus] = Field(None, description="Override default COMPLETED; e.g. FILTERED for dead-end")

    @classmethod
    def for_error(cls, item_id: str, stage: str, error: str, processing_time: float) -> "EndpointResponse":
        """Create response for a failed stage operation."""
        output = StageOperationResult(id=item_id, success=False, data=None, error_message=error).model_dump(mode='json')
        return cls(success=True, stage=stage, output=output, processing_time_seconds=round(processing_time, 2))
