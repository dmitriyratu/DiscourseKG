"""
Discovery pipeline component for DiscourseKG platform.

Orchestrates the discovery process using the autonomous agent.
"""

from typing import Dict, Any
from src.discover.discoverer import Discoverer
from src.discover.config import DiscoveryConfig
from src.shared.pipeline_definitions import StageResult


def discover_content(discovery_params: Dict[str, Any], config: DiscoveryConfig = None) -> StageResult:
    """Discover content from the provided parameters."""
    discoverer = Discoverer(config=config)
    return discoverer.discover_content(discovery_params)
