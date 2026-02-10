"""
Discovery pipeline component for DiscourseKG platform.

Orchestrates the discovery process using the autonomous agent.
"""

from src.discover.discoverer import Discoverer
from src.discover.config import DiscoveryConfig, discovery_config
from src.discover.models import DiscoveryRequest
from src.shared.pipeline_definitions import StageResult


def discover_content(discovery_params: DiscoveryRequest, config: DiscoveryConfig = discovery_config) -> StageResult:
    """Discover content from the provided parameters."""
    discoverer = Discoverer(config=config)
    return discoverer.discover_content(discovery_params)
