"""Configuration for discovery agent."""

import os
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class DiscoveryConfig(BaseModel):
    """Configuration for the discovery agent."""
    MIN_DATE_SCORE: int = Field(default=2, description="Minimum date score to accept an article")
    HEADLESS: bool = Field(default=False, description="Run browser in headless mode")
    MAX_PAGES: int = Field(default=5, description="Maximum pages to process per search URL")
    
    OPENAI_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv('OPENAI_API_KEY'))
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    OPENAI_TEMPERATURE: float = Field(default=0.0)
    
    model_config = {"frozen": True}


# Global instance
discovery_config = DiscoveryConfig()
