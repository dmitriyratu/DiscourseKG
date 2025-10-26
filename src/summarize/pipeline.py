"""
Summarization pipeline component for DiscourseKG platform.

Simple summarization function that will be called by an orchestrator.
"""

from typing import Dict, Any
from src.summarize.summarizer import Summarizer
from src.app_config import config


def preprocess_content(processing_context: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize content to target token count."""
    return Summarizer().summarize(processing_context)
