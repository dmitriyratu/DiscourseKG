"""
Summarization pipeline component for KG-Sentiment platform.

Simple summarization function that will be called by an orchestrator.
"""

from src.preprocessing.extractive_summarizer import ExtractiveSummarizer


def summarize_text(text: str, target_tokens: int):
    """Summarize text to target token count."""
    return ExtractiveSummarizer().summarize(text, target_tokens)