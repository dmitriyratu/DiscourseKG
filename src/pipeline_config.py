"""
Pipeline configuration for DiscourseKG platform.

Defines the pipeline stages and flow
"""

from typing import Optional
from enum import Enum


class PipelineStageStatus(str, Enum):
    """Status of a pipeline stage"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS" 
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    INVALIDATED = "INVALIDATED"


class PipelineStages(str, Enum):
    """Pipeline stage definitions - values match both directory names AND output field names"""
    DISCOVER = "discover"
    SCRAPE = "scrape"
    SUMMARIZE = "summarize"
    CATEGORIZE = "categorize"


class PipelineConfig:
    """Pipeline stage flow configuration"""
    
    # Define stage flow (what comes after each stage)
    STAGE_FLOW = {
        PipelineStages.DISCOVER: PipelineStages.SCRAPE,
        PipelineStages.SCRAPE: PipelineStages.SUMMARIZE,
        PipelineStages.SUMMARIZE: PipelineStages.CATEGORIZE, 
        PipelineStages.CATEGORIZE: None  # Pipeline complete
    }
    
    @classmethod
    def get_next_stage(cls, current_stage: str) -> Optional[str]:
        """Get the next stage after the current one"""
        return cls.STAGE_FLOW.get(current_stage)


# Export for easy importing
pipeline_config = PipelineConfig()
