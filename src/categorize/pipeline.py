"""
Categorization pipeline component for KG-Sentiment platform.

Simple categorization function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.categorize.content_categorizer import ContentCategorizer


def process_content(content_data: Dict[str, Any]) -> Dict[str, Any]:
    """Categorize content data."""
    return ContentCategorizer().categorize_content(content_data)
