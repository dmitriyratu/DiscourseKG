"""Extraction stage configuration."""

import os
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from dotenv import load_dotenv

load_dotenv()


class ExtractionConfig(BaseModel):
    """Settings for extraction stage LLM calls."""

    LLM_MODEL: str = Field(default="gpt-4o-mini")
    LLM_TEMPERATURE: float = Field(default=0.1)
    LLM_TIMEOUT: float = Field(default=60.0)
    LLM_MAX_RETRIES: int = Field(default=2)
    LLM_MAX_OUTPUT_TOKENS: int = Field(default=16384)
    LLM_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))

    CHUNK_SIZE: int = Field(default=6000, description="Max characters per chunk")
    CHUNK_OVERLAP: int = Field(default=500, description="Character overlap between chunks")
    MAX_CONCURRENT_CHUNKS: int = Field(default=50, description="Max parallel chunk calls")

    model_config = ConfigDict(frozen=True)


extraction_config = ExtractionConfig()
