"""
Simple data loader for pipeline stages.
"""

import json
from typing import Dict, Any

from src.shared.logging_utils import get_logger

logger = get_logger(__name__)


class DataLoader:
    """Loads JSON data for any pipeline stage."""
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """Load JSON data from file path."""
        logger.debug(f"Loading data from {file_path}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {file_path}: {e}")
    
    def extract_data_field(self, file_path: str, field: str) -> Any:
        """Extract a specific field from the nested data structure."""
        data = self.load(file_path)
        return data['data'].get(field, '')


