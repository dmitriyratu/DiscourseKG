"""
Summarization pipeline component for DiscourseKG platform.

Simple summarization function that will be called by an orchestrator.
"""

from src.summarize.summarizer import Summarizer
from src.summarize.models import SummarizeContext
from src.shared.pipeline_definitions import StageResult


def summarize_content(processing_context: SummarizeContext) -> StageResult:
    """Summarize content to target token count."""
    return Summarizer().summarize_content(processing_context)
