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
