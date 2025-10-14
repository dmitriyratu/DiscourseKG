"""
Preprocessing pipeline component for KG-Sentiment platform.

Simple preprocessing function that will be called by an orchestrator.
"""

from src.preprocessing.extractive_summarizer import ExtractiveSummarizer


def preprocess_content(text: str, target_tokens: int):
    """Preprocess content by summarizing to target token count."""
    return ExtractiveSummarizer().summarize(text, target_tokens)
