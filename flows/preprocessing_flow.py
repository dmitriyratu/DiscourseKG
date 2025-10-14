from prefect import flow, task
from datetime import datetime
from typing import Dict, Any
from tasks.orchestration import get_items
from src.shared.config import pipeline_stages
from src.shared.pipeline_state import PipelineStateManager
from src.schemas import PipelineStageStatus
from src.shared.logging_utils import setup_logger
from tasks.persistence import save_data
from src.preprocessing.summarize_endpoint import SummarizeEndpoint

logger = setup_logger("preprocessing_flow", "preprocessing_flow.log")


def save_summary(item_id: str, summary_result) -> str:
    """Save summary data."""
    return save_data(item_id, summary_result, 'summary')


@task(name="summarize_item", retries=2, retry_delay_seconds=30)
def summarize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Task to summarize article content."""
    logger = setup_logger("summarize_task", "preprocessing_flow.log")
    try:
        logger.info("Calling SummarizeEndpoint...")
        result = SummarizeEndpoint().execute(item)
        logger.info(f"Summarization completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error summarizing article: {str(e)}")
        raise


@flow
def preprocessing_flow():
    """Process items through preprocessing stage."""
    items = get_items(pipeline_stages.SUMMARIZE)
    logger.info(f"Found {len(items)} items to summarize")
    
    manager = PipelineStateManager()
    
    for item in items:
        # Process the item
        result = summarize_item.submit(item)
        
        # Wait for result and handle persistence/state updates
        if result.result()['success']:
            # Save the summary
            output_file = save_summary(
                result.result()['item_id'],
                result.result()['result']
            )
            
            # Update pipeline state
            manager.update_stage_status(
                result.result()['item_id'], 
                pipeline_stages.SUMMARIZE, 
                PipelineStageStatus.COMPLETED
            )
            
            logger.info(f"Completed summarization for item {result.result()['item_id']} -> {output_file}")
        else:
            # Handle failure
            manager.update_stage_status(
                result.result()['item_id'], 
                pipeline_stages.SUMMARIZE, 
                PipelineStageStatus.FAILED,
                error_message=result.result()['error']
            )
            logger.error(f"Failed summarization for item {result.result()['item_id']}: {result.result()['error']}")
    
    logger.info(f"Completed preprocessing flow for {len(items)} items")
