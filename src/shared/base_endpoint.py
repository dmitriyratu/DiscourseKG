"""
Base endpoint class for consistent interface across all pipeline endpoints.

Provides standardized execute method and common patterns for endpoint implementation.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from src.utils.logging_utils import get_logger
from src.shared.pipeline_definitions import EndpointResponse
from src.shared.pipeline_definitions import PipelineState


class BaseEndpoint(ABC):
    """Base class for all pipeline endpoints with standardized interface."""
    
    def __init__(self, endpoint_name: str) -> None:
        self.endpoint_name = endpoint_name
        self.logger = get_logger(endpoint_name)
    
    @abstractmethod
    def execute(self, state: PipelineState) -> EndpointResponse:
        """Execute the endpoint processing for a single item."""
        pass
    
    def _create_success_response(
        self,
        result: Any,
        stage: str,
        input_data: Optional[Any] = None,
        state_update: Optional[Dict[str, Any]] = None,
    ) -> EndpointResponse:
        """Create standardized success response."""
        return EndpointResponse(
            success=True,
            stage=stage,
            output=result,
            input_data=input_data,
            state_update=state_update
        )

