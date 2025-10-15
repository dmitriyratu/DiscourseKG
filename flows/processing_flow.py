from prefect import flow, task
from typing import Dict, Any
from src.pipeline_config import pipeline_stages
from src.shared.flow_processor import FlowProcessor
from src.shared.logging_utils import get_logger
from src.processing.categorize_endpoint import CategorizeEndpoint
from src.app_config import config

logger = get_logger(__name__)


@task(name="categorize_item", retries=2, retry_delay_seconds=30)
def categorize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Task to categorize article content."""
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
    processor = FlowProcessor("processing_flow")
    processor.process_items(
        stage=pipeline_stages.CATEGORIZE,
        task_func=categorize_item,
        data_type='categorization'
    )
