from prefect import flow, task
from src.shared.pipeline_definitions import PipelineStages, PipelineState
from src.shared.flow_processor import FlowProcessor
from src.shared.models import EndpointResponse
from src.utils.logging_utils import get_logger
from src.summarize.summarize_endpoint import SummarizeEndpoint
from pathlib import Path

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="summarize_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=120)
def summarize_item(state: PipelineState) -> EndpointResponse:
    """Task to summarize article content with error-aware retries."""
    try:
        result = SummarizeEndpoint().execute(state)
        return result
    except Exception as e:
        raise


@flow
def summarize_flow() -> None:
    """Process items through summarization stage."""
    logger.info(f"Starting {flow_name}")
    processor = FlowProcessor(flow_name)
    processor.process_items(
        stage=PipelineStages.SUMMARIZE,
        task_func=summarize_item
    )
    logger.info(f"Completed {flow_name}")
