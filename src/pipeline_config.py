"""
Pipeline configuration for KG-Sentiment platform.

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


class PipelineStages:
    """Pipeline stage definitions - values match directory names"""
    DISCOVERY = "discovery"
    SCRAPE = "scrape"
    SUMMARIZE = "summarize" 
    CATEGORIZE = "categorize"


class PipelineConfig:
    """Pipeline stage flow configuration"""
    
    # Define stage flow (what comes after each stage)
    STAGE_FLOW = {
        PipelineStages.DISCOVERY: PipelineStages.SCRAPE,
        PipelineStages.SCRAPE: PipelineStages.SUMMARIZE,
        PipelineStages.SUMMARIZE: PipelineStages.CATEGORIZE, 
        PipelineStages.CATEGORIZE: None  # Pipeline complete
    }
    
    # First stage to process (after raw data is available)
    FIRST_PROCESSING_STAGE = PipelineStages.SUMMARIZE
    
    @classmethod
    def get_next_stage(cls, current_stage: str) -> Optional[str]:
        """Get the next stage after the current one"""
        return cls.STAGE_FLOW.get(current_stage)
    
    @classmethod
    def is_pipeline_complete(cls, next_stage: Optional[str]) -> bool:
        """Check if the pipeline is complete"""
        return next_stage is None


# Export for easy importing
pipeline_stages = PipelineStages()
pipeline_config = PipelineConfig()
