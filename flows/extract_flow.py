from pathlib import Path

from prefect import flow, task

from src.extract.extract_endpoint import ExtractEndpoint
from src.shared.flow_processor import FlowProcessor
from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="extract_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=120)
def extract_item(state: PipelineState) -> EndpointResponse:
    return ExtractEndpoint().execute(state)


@flow
def extract_flow() -> None:
    logger.info(f"Starting {flow_name}")
    FlowProcessor(flow_name).process_items(stage=PipelineStages.EXTRACT, task_func=extract_item)
    logger.info(f"Completed {flow_name}")
