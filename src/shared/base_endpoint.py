"""
Base endpoint class for consistent interface across all pipeline endpoints.

Provides standardized execute method and common patterns for endpoint implementation.
"""

from typing import Optional
from abc import ABC, abstractmethod

from src.utils.logging_utils import get_logger
from src.shared.pipeline_definitions import (
    EndpointResponse, PipelineStageStatus, PipelineStages, PipelineState, StageResult,
)


class BaseEndpoint(ABC):
    """Base class for all pipeline endpoints with standardized interface."""
    
    def __init__(self, endpoint_name: str) -> None:
        self.endpoint_name = endpoint_name
        self.logger = get_logger(endpoint_name)
    
    @abstractmethod
    def execute(self, state: PipelineState) -> EndpointResponse:
        pass
    
    def _success(
        self,
        stage_result: StageResult,
        stage: PipelineStages,
        pipeline_status: Optional[PipelineStageStatus] = None,
    ) -> EndpointResponse:
        """Create standardized success response from a stage result."""
        return EndpointResponse(
            success=True,
            stage=stage.value,
            output=stage_result.artifact,
            state_update=stage_result.metadata,
            pipeline_status=pipeline_status,
        )

