from prefect import flow, task
from src.shared.pipeline_definitions import PipelineStages, PipelineState
from src.shared.flow_processor import FlowProcessor
from src.shared.models import EndpointResponse
from src.utils.logging_utils import get_logger
from src.categorize.categorize_endpoint import CategorizeEndpoint
from pathlib import Path

logger = get_logger(__name__)
flow_name = Path(__file__).stem

# In-memory cache for retry context (ephemeral, task-level only)
_retry_context = {}


@task(name="categorize_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=120)
def categorize_item(state: PipelineState) -> EndpointResponse:
    """Task to categorize article content with error-aware retries."""
    id = state.id
    
    # Load previous attempt's context if this is a retry
    if id in _retry_context:
        retry_ctx = _retry_context[id]
        # Update state with retry context for this attempt
        state = state.model_copy(update={
            'error_message': retry_ctx.get('error')
        })
        # Note: failed_output is handled via exception attribute, not state
    
    try:
        result = CategorizeEndpoint().execute(state)
        # Clean up cache on success
        _retry_context.pop(id, None)
        return result
    except Exception as e:
        # Store context for next retry attempt
        _retry_context[id] = {
            'error': str(e),
            'failed_output': getattr(e, 'failed_output', None)
        }
        raise


@flow
def categorize_flow() -> None:
    """Process items through categorization stage."""
    logger.info(f"Starting {flow_name}")
    processor = FlowProcessor(flow_name)
    processor.process_items(
        stage=PipelineStages.CATEGORIZE,
        task_func=categorize_item
    )
    logger.info(f"Completed {flow_name}")
