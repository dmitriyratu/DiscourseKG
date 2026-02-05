"""Summarization stage configuration."""

from pydantic import BaseModel, Field


class SummarizationConfig(BaseModel):
    """Settings for summarization processing."""
    
    # Target token count for summarized output
    TARGET_SUMMARY_TOKENS: int = Field(default=1000)
    
    # Model and tokenizer settings
    SUMMARIZER_MODEL: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model")
    SUMMARIZER_TOKENIZER: str = Field(default="cl100k_base", description="Tiktoken tokenizer")
    
    model_config = {"frozen": True}  # Make immutable


# Global instance
summarization_config = SummarizationConfig()

