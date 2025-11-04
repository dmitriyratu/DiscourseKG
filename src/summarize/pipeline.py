"""
Summarization pipeline component for DiscourseKG platform.

Simple summarization function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.summarize.summarizer import Summarizer


def summarize_content(processing_context: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize content to target token count."""
    return Summarizer().summarize_content(processing_context)
