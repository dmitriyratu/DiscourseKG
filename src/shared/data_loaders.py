"""
Simple data loader for pipeline stages.
"""

import json
from pathlib import Path
from typing import Dict, Any
import pyprojroot

from src.utils.logging_utils import get_logger
from src.shared.pipeline_definitions import PipelineStages

logger = get_logger(__name__)


class DataLoader:
    """Loads JSON data for any pipeline stage."""
    
    def load(self, file_path: str) -> Dict[str, Any]:
        """Load JSON data from file path (supports both relative and absolute paths)."""
        # Convert to Path object
        path = Path(file_path)
        
        # If path is not absolute, resolve it relative to project root
        if not path.is_absolute():
            path = pyprojroot.here() / path
        
        logger.debug(f"Loading data from {path}")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}")
    
    def extract_stage_output(self, file_path: str, stage: PipelineStages) -> Any:
        """Extract the output field from a specific stage's file."""
        data = self.load(file_path)
        return data['data'].get(stage.value, '')