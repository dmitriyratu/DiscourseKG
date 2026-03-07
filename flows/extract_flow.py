from pathlib import Path

from prefect import flow, task

from src.extract.extract_endpoint import ExtractEndpoint
from src.shared.flow_processor import FlowProcessor
from src.shared.pipeline_definitions import EndpointResponse, PipelineStages, PipelineState
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)
flow_name = Path(__file__).stem

_retry_context = {}


@task(name="extract_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=120)
def extract_item(state: PipelineState) -> EndpointResponse:
    """Task to extract entities and passages with error-aware retries."""
    id = state.id

    if id in _retry_context:
        retry_ctx = _retry_context[id]
        state = state.model_copy(update={
            'error_message': retry_ctx.get('error'),
            'previous_failed_output': retry_ctx.get('failed_output')
        })

    try:
        result = ExtractEndpoint().execute(state)
        _retry_context.pop(id, None)
        return result
    except Exception as e:
        _retry_context[id] = {
            'error': str(e),
            'failed_output': getattr(e, 'failed_output', None)
        }
        raise


@flow
def extract_flow() -> None:
    """Process items through extraction stage."""
    logger.info(f"Starting {flow_name}")
    processor = FlowProcessor(flow_name)
    processor.process_items(
        stage=PipelineStages.EXTRACT,
        task_func=extract_item
    )
    logger.info(f"Completed {flow_name}")
