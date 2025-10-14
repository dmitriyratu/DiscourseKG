"""
Pipeline task orchestration.

Provides clean task orchestration using stage-specific processors.
"""

from typing import List, Dict, Any
from prefect import task

from src.shared.pipeline_state import PipelineStateManager
from src.shared.config import pipeline_stages
from tasks.stage_processors import summarize_item, categorize_item
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


@task
def process_item(item: Dict[str, Any], stage: str) -> Dict[str, Any]:
    """
    Process one item through a stage using the appropriate processor.
    
    Args:
        item: Pipeline state item
        stage: Pipeline stage name
        
    Returns:
        Processing result dictionary
    """
    try:
        logger.info(f"Processing item {item['id']} through stage {stage}")
        
        if stage == pipeline_stages.SUMMARIZE:
            result = summarize_item(item)
        elif stage == pipeline_stages.CATEGORIZE:
            result = categorize_item(item)
        else:
            raise ValueError(f"Unknown stage: {stage}")
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to process item {item['id']} through stage {stage}: {str(e)}")
        return {
            'success': False,
            'item_id': item['id'],
            'stage': stage,
            'error': str(e)
        }