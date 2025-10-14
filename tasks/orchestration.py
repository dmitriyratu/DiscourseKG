"""
Pipeline task orchestration.

Provides clean task orchestration using stage-specific processors.
"""

from typing import List, Dict, Any

from src.shared.pipeline_state import PipelineStateManager
from src.shared.logging_utils import setup_logger

logger = setup_logger("flows_tasks", "flows_tasks.log")


def get_items(stage: str) -> List[Dict[str, Any]]:
    """
    Get items needing processing for a stage.
    
    Args:
        stage: Pipeline stage name
        
    Returns:
        List of pipeline state items ready for processing
    """
    manager = PipelineStateManager()
    items = manager.get_next_stage_tasks(stage)
    return [item.model_dump() for item in items]

