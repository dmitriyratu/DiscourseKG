"""Data models for scraping domain."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ScrapingData(BaseModel):
    """Scraped content data."""
    scrape: str = Field(..., description="The scraped content text")


class ScrapingResult(BaseModel):
    """Result of scraping operation with metrics and metadata."""
    id: str = Field(..., description="Unique identifier for the scraped content")
    success: bool = Field(..., description="Whether scraping was successful")
    data: Optional[ScrapingData] = Field(None, description="Scraped content data")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    error_message: Optional[str] = Field(None, description="Error message if scraping failed")

