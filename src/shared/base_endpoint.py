"""
Base endpoint class for consistent interface across all pipeline endpoints.

Provides standardized execute method and common patterns for endpoint implementation.
"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from src.utils.logging_utils import get_logger


class BaseEndpoint(ABC):
    """Base class for all pipeline endpoints with standardized interface."""
    
    def __init__(self, endpoint_name: str):
        self.endpoint_name = endpoint_name
        self.logger = get_logger(endpoint_name)
    
    @abstractmethod
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the endpoint processing for a single item."""
        pass
    
    def _create_success_response(
        self,
        result: Any,
        stage: str,
        input_data: Any = None,
        state_update: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create standardized success response."""
        response = {
            'success': True,
            'stage': stage,
            'output': result,
            'input_data': input_data,
            'state_update':state_update,
        }
        return response

