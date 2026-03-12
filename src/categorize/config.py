"""Categorization stage configuration."""

import os
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

load_dotenv()


class CategorizationConfig(BaseModel):
    """Quality thresholds and settings for categorization extraction (model-agnostic)."""
    
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_TEMPERATURE: float = Field(default=0.1)
    LLM_TIMEOUT: float = Field(default=60.0)
    LLM_MAX_RETRIES: int = Field(default=2)
    LLM_MAX_OUTPUT_TOKENS: int = Field(default=16384)
    LLM_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))
    
    MIN_PASSAGES_PER_CLAIM: int = Field(default=1, description="Minimum passages for a claim to be substantive")
    MIN_CONTEXT_LENGTH: int = Field(default=50, description="Minimum context string length (chars)")
    
    model_config = ConfigDict(frozen=True)

# Global instance
categorization_config = CategorizationConfig()

