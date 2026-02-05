from pathlib import Path
from typing import Dict, Any, List

from prefect import flow, task

from src.discover.discover_endpoint import DiscoverEndpoint
from src.shared.pipeline_definitions import PipelineStages
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="discover_content", retries=2, retry_delay_seconds=30, retry_jitter_factor=0.5, timeout_seconds=600)
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
    Discover articles and create initial pipeline states.
    
    Uses the autonomous discovery agent to search for speaker content
    within the specified date range.
    
    Args:
        speaker: Speaker identifier
        start_date: Start of date range (YYYY-MM-DD)
        end_date: End of date range (YYYY-MM-DD)
        search_urls: List of URLs to search for speaker content
    """
    logger.info(f"Starting {flow_name} for {speaker} from {start_date} to {end_date}")
    
    if search_urls:
        logger.info(f"Search URLs: {search_urls}")
    else:
        logger.warning(f"No search URLs provided for {speaker}")
    
    discovery_params = {
        'speaker': speaker,
        'start_date': start_date,
        'end_date': end_date,
        'search_urls': search_urls or []
    }
    
    result = discover_content.submit(discovery_params)
    result_data = result.result()
    
    if result_data['success']:
        data = result_data['output'].get('data', {})
        new_articles = data.get('new_articles', 0)
        total_found = data.get('total_found', 0)
        duplicates = data.get('duplicates_skipped', 0)
        
        logger.info(
            f"Discovery complete: {new_articles} new articles from {total_found} found "
            f"({duplicates} duplicates skipped)"
        )
        
        return {
            "status": "success",
            "new_articles": new_articles,
            "total_found": total_found,
            "duplicates_skipped": duplicates,
            "speaker": speaker,
            "date_range": f"{start_date} to {end_date}"
        }
    else:
        error = result_data.get('error', 'Unknown error')
        logger.error(f"Discovery failed: {error}")
        raise Exception(f"Discovery failed: {error}")
