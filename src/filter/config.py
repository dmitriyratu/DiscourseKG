"""Filter stage configuration."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class FilterConfig(BaseModel):
    """Settings for filter stage LLM calls (model-agnostic)."""
    
    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_TEMPERATURE: float = Field(default=0.0)
    LLM_TIMEOUT: float = Field(default=30.0)
    LLM_MAX_RETRIES: int = Field(default=2)
    LLM_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))
    CONTENT_PREVIEW_TOKENS: int = Field(default=10000, description="Max tokens of scrape text to send to LLM")
    
    model_config = {"frozen": True}

filter_config = FilterConfig()
