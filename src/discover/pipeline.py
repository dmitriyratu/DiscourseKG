"""
Discovery pipeline component for DiscourseKG platform.

Simple discovery function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.discover.discoverer import Discoverer


def discover_content(discovery_params: Dict[str, Any]) -> Dict[str, Any]:
    """Discover content from the provided parameters."""
    return Discoverer().discover_content(discovery_params)
