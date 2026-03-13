from pathlib import Path

from prefect import flow, task

from src.categorize.categorize_endpoint import CategorizeEndpoint
from src.shared.flow_processor import FlowProcessor
from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="categorize_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=120)
def categorize_item(state: PipelineState) -> EndpointResponse:
    return CategorizeEndpoint().execute(state)


@flow
def categorize_flow() -> None:
    logger.info(f"Starting {flow_name}")
    FlowProcessor(flow_name).process_items(stage=PipelineStages.CATEGORIZE, task_func=categorize_item)
    logger.info(f"Completed {flow_name}")
