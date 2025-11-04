"""
Pipeline task orchestration.

Provides clean task orchestration using stage-specific processors.
"""

from typing import List, Dict, Any

from src.shared.pipeline_state import PipelineStateManager
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def get_items(stage: str) -> List[Dict[str, Any]]:
    """Get items needing processing for a stage."""
    manager = PipelineStateManager()
    items = manager.get_next_stage_tasks(stage)
    return [item.model_dump() for item in items]