"""Data models for scraping domain."""

from pydantic import BaseModel, Field
from typing import Optional
from src.shared.models import StageOperationResult


class ScrapeContext(BaseModel):
    """Processing context for scraping operation."""
    id: str = Field(..., description="Unique identifier for the item")
    source_url: str = Field(..., description="URL to scrape content from")


class ScrapingData(BaseModel):
    """Scraped content data."""
    scrape: str = Field(..., description="The scraped transcript text")
    word_count: int = Field(..., description="Word count of scraped content")


class ScrapingResult(StageOperationResult[ScrapingData]):
    """Result of scraping operation."""
    pass


class DomainInfo(BaseModel):
    """Metadata for a domain extractor."""
    extractor_name: str = Field(..., description="Name of the extractor module in domains/")
    instructions: Optional[str] = Field(None, description="Custom LLM instructions for generation")


class ExtractorScript(BaseModel):
    """Structured output schema for LLM-generated extractor code."""
    code: str

