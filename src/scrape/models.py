"""Data models for scraping domain."""

from pydantic import BaseModel, Field
from typing import Optional
from src.shared.models import StageOperationResult


class ScrapeItem(BaseModel):
    """Input record required for scraping."""
    id: str = Field(..., description="Identifier of the pipeline item to scrape")
    source_url: str = Field(..., description="URL to scrape content from")


class ScrapeContext(BaseModel):
    """Processing context for scraping operation."""
    id: str = Field(..., description="Unique identifier for the item")
    source_url: str = Field(..., description="URL to scrape content from")


class ScrapingData(BaseModel):
    """Scraped content data."""
    scrape: str = Field(..., description="The scraped transcript text")
    word_count: int = Field(..., description="Word count of scraped content")


class ScrapingResult(StageOperationResult[ScrapingData]):
    """Result of scraping operation (artifact only, no metadata)."""
    pass

