"""Data models for scraping domain."""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any


class ScrapeItem(BaseModel):
    """Input record required for scraping."""
    id: str = Field(..., description="Identifier of the pipeline item to scrape")
    source_url: str = Field(..., description="URL to scrape content from")
    speaker: Optional[str] = Field(None, description="Speaker associated with the content")
    content_type: Optional[str] = Field(None, description="Type of content to scrape")
    content_date: Optional[str] = Field(None, description="Date of the content")


class ScrapeContext(BaseModel):
    """Processing context for scraping operation."""
    id: str = Field(..., description="Unique identifier for the item")
    source_url: str = Field(..., description="URL to scrape content from")


class ScrapingData(BaseModel):
    """Scraped content data."""
    scrape: str = Field(..., description="The scraped content text")
    word_count: int = Field(..., description="Word count of scraped content")
    title: Optional[str] = Field(None, description="Title of the scraped content")
    content_date: Optional[str] = Field(None, description="Date of the content")
    content_type: Optional[str] = Field(None, description="Type of content (speech, interview, debate)")


class ScrapingResult(BaseModel):
    """Result of scraping operation (artifact only, no metadata)."""
    id: str = Field(..., description="Unique identifier for the scraped content")
    success: bool = Field(..., description="Whether scraping was successful")
    data: Optional[ScrapingData] = Field(None, description="Scraped content data")
    error_message: Optional[str] = Field(None, description="Error message if scraping failed")

