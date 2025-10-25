"""
Categorization pipeline component for DiscourseKG platform.

Simple categorization function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.categorize.categorizer import Categorizer


def process_content(content_data: Dict[str, Any]) -> Dict[str, Any]:
    """Categorize content data."""
    return Categorizer().categorize_content(content_data)
