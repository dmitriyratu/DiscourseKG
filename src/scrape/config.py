"""Scraping stage configuration."""

from pydantic import BaseModel, Field


class ScraperConfig(BaseModel):
    """Configuration for scraping operations."""
    
    DEFAULT_INSTRUCTIONS: str = Field(
        default="Extract the primary content structure preserving meaningful information"
    )
    HTML_SAMPLE_MAX_CHARS: int = Field(default=30000)
    LLM_MODEL: str = Field(default="claude-sonnet-4-5")

    model_config = {"frozen": True}


scraper_config = ScraperConfig()
