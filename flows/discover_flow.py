from prefect import flow, task
from typing import List, Optional
from pathlib import Path

from src.shared.pipeline_definitions import PipelineStages, EndpointResponse
from src.utils.logging_utils import get_logger
from src.discover.discover_endpoint import DiscoverEndpoint
from src.discover.models import DiscoveryResult, DiscoveryRequest

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="discover_content", retries=2, retry_delay_seconds=30, retry_jitter_factor=0.5, timeout_seconds=1000)
def discover_content(discovery_params: DiscoveryRequest) -> EndpointResponse:
    """Task to discover content sources with error-aware retries."""
    result = DiscoverEndpoint().execute(discovery_params)
    return result


@flow
def discover_flow(speaker: str, start_date: str, end_date: Optional[str] = None, search_urls: Optional[List[str]] = None) -> None:
    """
    Entry point flow: Discover articles and create initial pipeline states.
    
    Uses the autonomous discovery agent to search for speaker content
    within the specified date range.
    """
    logger.info(f"Starting {flow_name} for {speaker} from {start_date} to {end_date or 'present'}")
    
    discovery_params = DiscoveryRequest(
        speaker=speaker,
        start_date=start_date,
        end_date=end_date,
        search_urls=search_urls or []
    )
    
    result = discover_content.submit(discovery_params)
    result_data = result.result()
    
    # Parse output using DiscoveryResult model
    discovery_result = DiscoveryResult.model_validate(result_data.output)
    
    if not discovery_result.success:
        error = discovery_result.error_message or 'Unknown error'
        logger.error(f"Discovery failed: {error}")
        raise Exception(f"Discovery failed: {error}")
    
    logger.info(f"Completed {flow_name}")
