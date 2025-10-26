from prefect import flow, task
from typing import Dict, Any
from src.pipeline_config import PipelineStages
from src.shared.flow_processor import FlowProcessor
from src.utils.logging_utils import get_logger
from src.discover.discover_endpoint import DiscoverEndpoint
from pathlib import Path

logger = get_logger(__name__)
flow_name = Path(__file__).stem


@task(name="discover_content", retries=2, retry_delay_seconds=30)
def discover_content(discovery_params: Dict[str, Any]) -> Dict[str, Any]:
    """Task to discover content sources."""
    try:
        result = DiscoverEndpoint().execute(discovery_params)
        return result
    except Exception as e:
        logger.error(f"{flow_name} failed for speaker {discovery_params.get('speaker', 'unknown')}: {str(e)}")
        raise


@flow
def discover_flow(speaker: str, start_date: str, end_date: str):
    """
    Discover items and create initial pipeline states.
    
    This flow handles the discovery of items to be processed and creates
    initial pipeline state records for each discovered item.
    """
    logger.info(f"Starting {flow_name} for {speaker} from {start_date} to {end_date}")
    
    # Create discovery parameters
    discovery_params = {
        'speaker': speaker,
        'start_date': start_date,
        'end_date': end_date
    }
    
    # Process discovery
    result = discover_content.submit(discovery_params)
    result_data = result.result()
    
    if result_data['success']:
        discovered_count = len(result_data['output'].get('discovered_items', []))
        logger.info(f"Discovery complete - created {discovered_count} pipeline states")
        
        return {
            "status": "success", 
            "discovered_items": discovered_count,
            "speaker": speaker,
            "date_range": f"{start_date} to {end_date}"
        }
    else:
        logger.error(f"Discovery failed: {result_data.get('error', 'Unknown error')}")
        raise Exception(f"Discovery failed: {result_data.get('error', 'Unknown error')}")
