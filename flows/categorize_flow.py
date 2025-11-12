from prefect import flow, task
from typing import Dict, Any
from src.shared.pipeline_definitions import PipelineStages
from src.shared.flow_processor import FlowProcessor
from src.utils.logging_utils import get_logger
from src.categorize.categorize_endpoint import CategorizeEndpoint
from pathlib import Path

logger = get_logger(__name__)
flow_name = Path(__file__).stem

# In-memory cache for retry context (ephemeral, task-level only)
_retry_context = {}


@task(name="categorize_item", retries=2, retry_delay_seconds=10, retry_jitter_factor=0.5, timeout_seconds=120)
def categorize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """Task to categorize article content with error-aware retries."""
    id = item['id']
    
    # Load previous attempt's context if this is a retry
    if id in _retry_context:
        retry_ctx = _retry_context[id]
        item['error_message'] = retry_ctx.get('error')
        item['failed_output'] = retry_ctx.get('failed_output')
    
    try:
        result = CategorizeEndpoint().execute(item)
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
def categorize_flow():
    """Process items through categorization stage."""
    logger.info(f"Starting {flow_name}")
    processor = FlowProcessor(flow_name)
    processor.process_items(
        stage=PipelineStages.CATEGORIZE.value,
        task_func=categorize_item,
        data_type=PipelineStages.CATEGORIZE.value
    )
    logger.info(f"Completed {flow_name}")
