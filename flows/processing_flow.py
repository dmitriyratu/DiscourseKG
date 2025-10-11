from prefect import flow
from flows.tasks import get_items, process_item
from pipeline.config import pipeline_stages
from src.utils.logging_utils import setup_logger

logger = setup_logger("processing_flow", "processing_flow.log")


@flow
def processing_flow():
    """Process items through categorization stage."""
    items = get_items(pipeline_stages.CATEGORIZE)
    logger.info(f"Found {len(items)} items to categorize")
    
    for item in items:
        process_item.submit(item, pipeline_stages.CATEGORIZE)
    
    logger.info(f"Submitted {len(items)} categorization tasks")
