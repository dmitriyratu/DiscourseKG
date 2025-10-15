"""
Summarization pipeline component for KG-Sentiment platform.

Simple summarization function that will be called by an orchestrator.
"""

from src.summarize.extractive_summarizer import ExtractiveSummarizer


def preprocess_content(id: str, text: str, target_tokens: int):
    """Summarize content to target token count."""
    return ExtractiveSummarizer().summarize(id, text, target_tokens)
