"""Categorization stage configuration."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class CategorizationConfig(BaseModel):
    """Quality thresholds and settings for categorization extraction."""
    
    # OpenAI Configuration (used for structured extraction)
    OPENAI_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_MAX_OUTPUT_TOKENS: int = Field(default=10000)
    OPENAI_TEMPERATURE: float = Field(default=0.1)
    OPENAI_TIMEOUT: float = Field(default=60.0)
    OPENAI_MAX_RETRIES: int = Field(default=2)
    
    # Quality Filters - Define what constitutes a "substantive" mention
    MIN_QUOTES_PER_MENTION: int = Field(default=1, description="Minimum quotes for a mention to be substantive")
    MIN_CONTEXT_LENGTH: int = Field(default=50, description="Minimum context string length (chars)")
    
    model_config = {"frozen": True}  # Make immutable like a config should be

# Global instance
categorization_config = CategorizationConfig()

