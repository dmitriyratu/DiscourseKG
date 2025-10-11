from prefect import flow
from flows.tasks import get_items, process_item
from pipeline.config import pipeline_stages
from src.utils.logging_utils import setup_logger

logger = setup_logger("preprocessing_flow", "preprocessing_flow.log")


@flow
def preprocessing_flow():
    """Process items through preprocessing stage."""
    items = get_items(pipeline_stages.SUMMARIZE)
    logger.info(f"Found {len(items)} items to summarize")
    
    for item in items:
        process_item.submit(item, pipeline_stages.SUMMARIZE)
    
    logger.info(f"Submitted {len(items)} summarization tasks")
