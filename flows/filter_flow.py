"""Filter flow: identify tracked speakers and dead-end irrelevant articles."""

from prefect import flow, task
from pathlib import Path

from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.shared.flow_processor import FlowProcessor
from src.filter.filter_endpoint import FilterEndpoint
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="filter_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=60)
def filter_item(state: PipelineState) -> EndpointResponse:
    """Task to filter article content with error-aware retries."""
    return FilterEndpoint().execute(state)


@flow
def filter_flow() -> None:
    """Process items through filter stage, routing FILTERED vs COMPLETED."""
    logger.info(f"Starting {flow_name}")
    processor = FlowProcessor(flow_name)
    processor.process_items(stage=PipelineStages.FILTER, task_func=filter_item)
    logger.info(f"Completed {flow_name}")
