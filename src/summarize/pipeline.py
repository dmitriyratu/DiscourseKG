"""
Summarization pipeline component for DiscourseKG platform.

Simple summarization function that will be called by an orchestrator.
"""

from src.summarize.summarizer import Summarizer


def preprocess_content(id: str, text: str, target_tokens: int):
    """Summarize content to target token count."""
    return Summarizer().summarize(id, text, target_tokens)
