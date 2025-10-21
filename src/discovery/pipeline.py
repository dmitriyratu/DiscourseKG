"""
Discovery pipeline component for KG-Sentiment platform.

Simple discovery function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.discovery.discovery_agent import DiscoveryAgent


def discover_content(discovery_params: Dict[str, Any]) -> Dict[str, Any]:
    """Discover content from the provided parameters."""
    return DiscoveryAgent().discover_content(discovery_params)
