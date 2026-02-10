"""
Pipeline task orchestration.

Provides clean task orchestration using stage-specific processors.
"""

from typing import List

from src.shared.pipeline_state import PipelineStateManager
from src.shared.pipeline_definitions import PipelineState, PipelineStages
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


def get_items(stage: PipelineStages) -> List[PipelineState]:
    """Get items needing processing for a stage."""
    manager = PipelineStateManager()
    return manager.get_next_stage_tasks(stage)