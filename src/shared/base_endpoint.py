"""
Base endpoint class for consistent interface across all pipeline endpoints.

Provides standardized execute method and common patterns for endpoint implementation.
"""

from typing import Dict, Any
from abc import ABC, abstractmethod
from src.shared.logging_utils import get_logger


class BaseEndpoint(ABC):
    """Base class for all pipeline endpoints with standardized interface."""
    
    def __init__(self, endpoint_name: str):
        self.endpoint_name = endpoint_name
        self.logger = get_logger(endpoint_name)
    
    @abstractmethod
    def execute(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the endpoint processing for a single item.
        
        Args:
            item: Dictionary containing all necessary data for processing
            
        Returns:
            Dictionary with success status and results
        """
        pass
    
    def _create_success_response(self, item_id: str, result: Any, stage: str, input_data: Any = None) -> Dict[str, Any]:
        """Create standardized success response."""
        return {
            'success': True,
            'item_id': item_id,
            'stage': stage,
            'result': result,
            'input_data': input_data
        }
    
    def _create_error_response(self, item_id: str, stage: str, error: str) -> Dict[str, Any]:
        """Create standardized error response."""
        return {
            'success': False,
            'item_id': item_id,
            'stage': stage,
            'error': error
        }
