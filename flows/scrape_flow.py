from prefect import flow, task
from typing import Dict, Any
from src.shared.pipeline_definitions import PipelineStages
from src.shared.flow_processor import FlowProcessor
from src.utils.logging_utils import get_logger
from src.scrape.scrape_endpoint import ScrapeEndpoint
from pathlib import Path

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="scrape_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=120)
def scrape_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Task to scrape article content with error-aware retries."""
    try:
        result = ScrapeEndpoint().execute(item)
        return result
    except Exception as e:
        # Store error in item for next retry attempt (already logged at origin)
        item['error_message'] = str(e)
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