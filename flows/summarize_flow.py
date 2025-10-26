from prefect import flow, task
from typing import Dict, Any
from src.pipeline_config import PipelineStages
from src.shared.flow_processor import FlowProcessor
from src.utils.logging_utils import get_logger
from src.summarize.summarize_endpoint import SummarizeEndpoint
from pathlib import Path

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="summarize_item", retries=2, retry_delay_seconds=30, retry_jitter_factor=0.5)
def summarize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Task to summarize article content with error-aware retries."""
    try:
        result = SummarizeEndpoint().execute(item)
        return result
    except Exception as e:
        error_msg = str(e)
        logger.error(f"{flow_name} failed for item {item.get('id', 'unknown')}: {error_msg}")
        item['error_message'] = error_msg
        raise


@flow
def summarize_flow():
    """Process items through summarization stage."""
    logger.info(f"Starting {flow_name}")
    processor = FlowProcessor(flow_name)
    processor.process_items(
        stage=PipelineStages.SUMMARIZE.value,
        task_func=summarize_item,
        data_type=PipelineStages.SUMMARIZE.value
    )
    logger.info(f"Completed {flow_name}")
