from prefect import flow, task
from typing import Dict, Any
from src.pipeline_config import PipelineStages
from src.shared.flow_processor import FlowProcessor
from src.utils.logging_utils import get_logger
from src.graph.graph_endpoint import GraphEndpoint
from pathlib import Path

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="graph_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=60)
def graph_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Task to preprocess data for graph with error-aware retries."""
    try:
        result = GraphEndpoint().execute(item)
        return result
    except Exception as e:
        # Store error in item for next retry attempt (already logged at origin)
        item['error_message'] = str(e)
        raise


@flow
def graph_flow():
    """Process items through graph preprocessing stage."""
    logger.info(f"Starting {flow_name}")
    processor = FlowProcessor(flow_name)
    processor.process_items(
        stage=PipelineStages.GRAPH.value,
        task_func=graph_item,
        data_type=PipelineStages.GRAPH.value
    )
    logger.info(f"Completed {flow_name}")

