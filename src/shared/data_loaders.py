"""
Simple data loader for pipeline stages.
"""

import json
from pathlib import Path
from typing import Any, Dict
import pyprojroot

from src.utils.logging_utils import get_logger
from src.shared.pipeline_definitions import PipelineStages, PipelineState

logger = get_logger(__name__)


class DataLoader:
    """Loads JSON data for any pipeline stage."""

    @staticmethod
    def load(file_path: str) -> Dict[str, Any]:
        """Load JSON data from file path (supports both relative and absolute paths)."""
        path = Path(file_path)
        if not path.is_absolute():
            path = pyprojroot.here() / path
        logger.debug(f"Loading data from {path}")
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {path}: {e}")

    @staticmethod
    def extract_stage_output(file_path: str, stage: PipelineStages) -> Any:
        """Extract the output field from a specific stage's file."""
        data = DataLoader.load(file_path)
        return data['data'].get(stage.value, '')

    @staticmethod
    def load_content_input(state: PipelineState, *stages: PipelineStages) -> str:
        """Load content from first stage that has it. Raises ValueError if none have content."""
        for stage in stages:
            path = state.get_file_path_for_stage(stage.value)
            if path:
                content = DataLoader.extract_stage_output(path, stage)
                if content and str(content).strip():
                    return str(content)
        raise ValueError("Empty content")