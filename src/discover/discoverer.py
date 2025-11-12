"""
Discoverer for finding content sources.

This module handles the discovery of content sources for the DiscourseKG platform.
Currently uses mock discovery - will be replaced with real agent-based discovery.
"""

import time
from datetime import datetime
from typing import Dict, Any, List
from src.shared.pipeline_state import PipelineStateManager
from src.discover.models import DiscoveredItem, DiscoveryData, DiscoveryResult
from src.shared.pipeline_definitions import StageResult
from src.utils.logging_utils import get_logger

logger = get_logger(__name__)


class Discoverer:
    """
    Discoverer for finding content sources.
    
    This class handles the discovery of content sources for the
    knowledge graph platform. Currently uses mock discovery but
    will be replaced with real agent-based discovery.
    """
    
    def __init__(self):
        logger.debug("Discoverer initialized")
    
    def discover_content(self, discovery_params: Dict[str, Any]) -> StageResult:
        """Discover content sources based on the provided parameters."""
        speaker = discovery_params['speaker']
        start_date = discovery_params['start_date']
        end_date = discovery_params['end_date']
        
        start_time = time.time()
        logger.debug(f"Starting discovery for speaker: {speaker}")
        
        # Generate timestamp once for this discovery run
        discovery_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        run_timestamp = datetime.now().strftime("%Y-%m-%d_%H:%M:%S")
        
        # Mock discovery - in real implementation this would use agents to find content
        mock_urls = [
            f"https://example.com/test/speech_{i}_{discovery_timestamp}"
            for i in range(3)
        ]
        
        manager = PipelineStateManager()
        discovered_items = []
        
        # Create states for all discovered items
        for i, url in enumerate(mock_urls):
            content_types = ["speech", "interview", "debate"]
            content_type = content_types[i % len(content_types)]
            
            # Generate unique ID with index to ensure uniqueness
            item_id = f"discovered-item-{i}-{discovery_timestamp}"
            
            # Create initial pipeline state
            state = manager.create_state(
                id=item_id,
                run_timestamp=run_timestamp,
                source_url=url,
                speaker=speaker,
                content_type=content_type
            )
            
            discovered_item = DiscoveredItem(
                id=state.id,
                source_url=url,
                speaker=speaker,
                content_type=content_type
            )
            discovered_items.append(discovered_item)
            
            logger.debug(f"Created state for discovered item: {item_id}")
        
        processing_time = round(time.time() - start_time, 2)
        logger.debug(f"Successfully discovered {len(discovered_items)} items ({processing_time}s)")
        
        return self._create_result(discovered_items, speaker, start_date, end_date, discovery_timestamp)
    
    def _create_result(self, discovered_items: List[DiscoveredItem], 
                       speaker: str, start_date: str, end_date: str,
                       discovery_timestamp: str) -> StageResult:
        """Helper to create StageResult with separated artifact and metadata."""
        discovery_data = DiscoveryData(
            discovery_id=f"discovery-{discovery_timestamp}",
            discovered_items=discovered_items,
            speaker=speaker,
            date_range=f"{start_date} to {end_date}",
            item_count=len(discovered_items)
        )
        
        artifact = DiscoveryResult(
            success=True,
            data=discovery_data,
            error_message=None
        )
        
        return StageResult(artifact=artifact.model_dump(), metadata=None)