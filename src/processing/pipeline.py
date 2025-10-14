"""
Processing pipeline component for KG-Sentiment platform.

Simple processing function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.processing.content_categorizer import ContentCategorizer


def process_content(content_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process content data through categorization."""
    return ContentCategorizer().categorize_content(content_data)
