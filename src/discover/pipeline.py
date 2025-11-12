"""
Discovery pipeline component for DiscourseKG platform.

Simple discovery function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.discover.discoverer import Discoverer
from src.shared.pipeline_definitions import StageResult


def discover_content(discovery_params: Dict[str, Any]) -> StageResult:
    """Discover content from the provided parameters."""
    return Discoverer().discover_content(discovery_params)
