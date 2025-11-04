"""Summarization stage configuration."""


class SummarizationConfig:
    """Settings for summarization processing."""
    
    # Target token count for summarized output
    TARGET_SUMMARY_TOKENS: int = 1000
    
    # Model and tokenizer settings
    SUMMARIZER_MODEL: str = "all-MiniLM-L6-v2"  # Sentence transformer model
    SUMMARIZER_TOKENIZER: str = "cl100k_base"  # Tiktoken tokenizer


# Global instance
summarization_config = SummarizationConfig()

