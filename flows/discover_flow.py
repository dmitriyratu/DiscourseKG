from prefect import flow, task
from typing import Dict, Any, List
from pathlib import Path

from src.shared.pipeline_definitions import PipelineStages
from src.utils.logging_utils import get_logger
from src.discover.discover_endpoint import DiscoverEndpoint

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="discover_content", retries=2, retry_delay_seconds=30, retry_jitter_factor=0.5, timeout_seconds=1000)
def discover_content(discovery_params: Dict[str, Any]) -> Dict[str, Any]:
    """Task to discover content sources with error-aware retries."""
    try:
        result = DiscoverEndpoint().execute(discovery_params)
        return result
    except Exception as e:
        discovery_params['error_message'] = str(e)
        raise


@flow
def discover_flow(speaker: str, start_date: str, end_date: str, search_urls: List[str] = None):
    """
    Entry point flow: Discover articles and create initial pipeline states.
    
    Uses the autonomous discovery agent to search for speaker content
    within the specified date range.
    """
    logger.info(f"Starting {flow_name} for {speaker} from {start_date} to {end_date}")
    
    discovery_params = {
        'speaker': speaker,
        'start_date': start_date,
        'end_date': end_date,
        'search_urls': search_urls or []
    }
    
    result = discover_content.submit(discovery_params)
    result_data = result.result()
    
    if not result_data['success']:
        error = result_data.get('error', 'Unknown error')
        logger.error(f"Discovery failed: {error}")
        raise Exception(f"Discovery failed: {error}")
    
    data = result_data['output'].get('data', {})
    logger.info(
        f"Discovery complete: {data.get('new_articles', 0)} new articles "
        f"from {data.get('total_found', 0)} found "
        f"({data.get('duplicates_skipped', 0)} duplicates skipped)"
    )
    
    logger.info(f"Completed {flow_name}")
