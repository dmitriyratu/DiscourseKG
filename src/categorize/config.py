"""Categorization stage configuration."""

import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class CategorizationConfig:
    """Quality thresholds and settings for categorization extraction."""
    
    # OpenAI Configuration (used for structured extraction)
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_OUTPUT_TOKENS: int = 10000
    OPENAI_TEMPERATURE: float = 0.1
    OPENAI_TIMEOUT: float = 60.0
    OPENAI_MAX_RETRIES: int = 2
    
    # Quality Filters - Define what constitutes a "substantive" mention
    MIN_QUOTES_PER_MENTION: int = 1  # Minimum quotes for a mention to be substantive
    MIN_CONTEXT_LENGTH: int = 50  # Minimum context string length (chars)

# Global instance
categorization_config = CategorizationConfig()

