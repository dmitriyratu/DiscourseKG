"""
Pipeline stage definitions and flow configuration.

Used across the DiscourseKG pipeline to keep stage enums, status
constants, and shared data models centralized.
"""

from typing import Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field


class PipelineStageStatus(str, Enum):
    """Status of a pipeline stage."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"


class PipelineStages(str, Enum):
    """Pipeline stage definitions; values match directory names and data keys."""

    DISCOVER = "discover"
    SCRAPE = "scrape"
    SUMMARIZE = "summarize"
    CATEGORIZE = "categorize"
    GRAPH = "graph"


class PipelineConfig:
    """Pipeline stage flow configuration."""

    STAGE_FLOW = {
        PipelineStages.DISCOVER: PipelineStages.SCRAPE,
        PipelineStages.SCRAPE: PipelineStages.SUMMARIZE,
        PipelineStages.SUMMARIZE: PipelineStages.CATEGORIZE,
        PipelineStages.CATEGORIZE: PipelineStages.GRAPH,
        PipelineStages.GRAPH: None,
    }

    @classmethod
    def get_next_stage(cls, current_stage: str) -> Optional[str]:
        """Get the next stage after the current one."""

        return cls.STAGE_FLOW.get(current_stage)


class StageResult(BaseModel):
    """Result from a pipeline stage with separated artifact and metadata."""
    
    artifact: Dict[str, Any] = Field(..., description="Data to persist as stage output file")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata for pipeline state updates only")


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
    speaker: Optional[str] = Field(None, description="Primary speaker name")
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

    def get_current_file_path(self) -> Optional[str]:
        """Get file path for the latest completed stage"""
        if self.latest_completed_stage and self.latest_completed_stage in self.stages:
            return self.stages[self.latest_completed_stage].file_path
        return None
    
    def get_file_path_for_stage(self, stage: str) -> Optional[str]:
        """Get file path for a specific stage"""
        if stage in self.stages:
            return self.stages[stage].file_path
        return None


class EndpointResponse(BaseModel):
    """Standardized response from pipeline endpoints."""
    success: bool = Field(..., description="Whether endpoint execution was successful")
    stage: str = Field(..., description="Pipeline stage name")
    output: Dict[str, Any] = Field(..., description="Stage operation result (contains StageOperationResult structure)")
    input_data: Optional[Any] = Field(None, description="Input data passed to endpoint")
    state_update: Optional[Dict[str, Any]] = Field(None, description="Metadata for pipeline state updates")
    processing_time_seconds: Optional[float] = Field(None, description="Processing time in seconds (added by flow processor)")
