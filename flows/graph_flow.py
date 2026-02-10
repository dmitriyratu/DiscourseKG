from prefect import flow, task
from src.shared.pipeline_definitions import PipelineStages, PipelineState
from src.shared.flow_processor import FlowProcessor
from src.shared.models import EndpointResponse
from src.utils.logging_utils import get_logger
from src.graph.graph_endpoint import GraphEndpoint
from pathlib import Path

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="graph_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=60)
def graph_item(state: PipelineState) -> EndpointResponse:
    """Task to preprocess data for graph with error-aware retries."""
    try:
        result = GraphEndpoint().execute(state)
        return result
    except Exception as e:
        raise


@flow
def graph_flow() -> None:
    """Process items through graph preprocessing stage."""
    logger.info(f"Starting {flow_name}")
    processor = FlowProcessor(flow_name)
    processor.process_items(
        stage=PipelineStages.GRAPH,
        task_func=graph_item
    )
    logger.info(f"Completed {flow_name}")

