from prefect import flow, task
from datetime import datetime
from typing import Dict, Any
from tasks.orchestration import get_items
from src.shared.config import pipeline_stages
from src.shared.pipeline_state import PipelineStateManager
from src.schemas import PipelineStageStatus
from src.shared.logging_utils import setup_logger
from tasks.persistence import save_data
from src.processing.categorize_endpoint import CategorizeEndpoint

logger = setup_logger("processing_flow", "processing_flow.log")


def save_categorization(item_id: str, categorization_result: dict) -> str:
    """Save categorization data."""
    return save_data(item_id, categorization_result, 'categorization')


@task(name="categorize_item", retries=2, retry_delay_seconds=30)
def categorize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Task to categorize article content."""
    logger = setup_logger("categorize_task", "processing_flow.log")
    try:
        logger.info("Calling CategorizeEndpoint...")
        result = CategorizeEndpoint().execute(item)
        logger.info(f"Categorization completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error categorizing article: {str(e)}")
        raise


@flow
def processing_flow():
    """Process items through categorization stage."""
    items = get_items(pipeline_stages.CATEGORIZE)
    logger.info(f"Found {len(items)} items to categorize")
    
    manager = PipelineStateManager()
    
    for item in items:
        # Process the item
        result = categorize_item.submit(item)
        
        # Wait for result and handle persistence/state updates
        if result.result()['success']:
            # Save the categorization
            output_file = save_categorization(
                result.result()['item_id'],
                result.result()['result']
            )
            
            # Update pipeline state
            manager.update_stage_status(
                result.result()['item_id'], 
                pipeline_stages.CATEGORIZE, 
                PipelineStageStatus.COMPLETED
            )
            
            logger.info(f"Completed categorization for item {result.result()['item_id']} -> {output_file}")
        else:
            # Handle failure
            manager.update_stage_status(
                result.result()['item_id'], 
                pipeline_stages.CATEGORIZE, 
                PipelineStageStatus.FAILED,
                error_message=result.result()['error']
            )
            logger.error(f"Failed categorization for item {result.result()['item_id']}: {result.result()['error']}")
    
    logger.info(f"Completed processing flow for {len(items)} items")
