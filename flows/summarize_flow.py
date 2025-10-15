from prefect import flow, task
from typing import Dict, Any
from src.pipeline_config import pipeline_stages, PipelineStages
from src.shared.flow_processor import FlowProcessor
from src.shared.logging_utils import get_logger
from src.summarize.summarize_endpoint import SummarizeEndpoint

logger = get_logger(__name__)


@task(name="summarize_item", retries=2, retry_delay_seconds=30)
def summarize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Task to summarize article content."""
    try:
        logger.info("Calling SummarizeEndpoint...")
        result = SummarizeEndpoint().execute(item)
        logger.info(f"Summarization completed: {result}")
        return result
    except Exception as e:
        logger.error(f"Error summarizing article: {str(e)}")
        raise


@flow
def summarize_flow():
    """Process items through summarization stage."""
    processor = FlowProcessor("summarize_flow")
    processor.process_items(
        stage=pipeline_stages.SUMMARIZE,
        task_func=summarize_item,
        data_type=PipelineStages.SUMMARIZE
    )
