from prefect import flow, task
from typing import Dict, Any
from src.pipeline_config import PipelineStages
from src.shared.flow_processor import FlowProcessor
from src.utils.logging_utils import get_logger
from src.scrape.scrape_endpoint import ScrapeEndpoint
from pathlib import Path

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="scrape_item", retries=2, retry_delay_seconds=30, retry_jitter_factor=0.5)
def scrape_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Task to scrape article content with error-aware retries."""
    try:
        result = ScrapeEndpoint().execute(item)
        return result
    except Exception as e:
        error_msg = str(e)
        logger.error(f"{flow_name} failed for item {item.get('id', 'unknown')}: {error_msg}")
        item['error_message'] = error_msg
        raise


@flow
def scrape_flow():
    """Process items through scraping stage."""
    logger.info(f"Starting {flow_name}")
    processor = FlowProcessor(flow_name)
    processor.process_items(
        stage=PipelineStages.SCRAPE.value,
        task_func=scrape_item,
        data_type=PipelineStages.SCRAPE.value
    )
    logger.info(f"Completed {flow_name}")