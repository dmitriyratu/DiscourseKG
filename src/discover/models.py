"""
Pydantic models for the discovery stage.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from src.discover.agent.models import DateSource


class DiscoveredArticle(BaseModel):
    """Article discovered by the discovery agent."""
    id: str = Field(..., description="Unique identifier (format: YYYY-MM-DD-title-slug-hash)")
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    publication_date: str = Field(..., description="Publication date (YYYY-MM-DD)")
    date_score: int = Field(..., description="Confidence score for the date")
    date_source: str = Field(..., description="Source of the date (datetime_attr, url_path, etc.)")
    speaker: str = Field(..., description="Speaker associated with the article")


class DiscoveredItem(BaseModel):
    """Legacy model - kept for backwards compatibility."""
    id: str = Field(..., description="Unique identifier for the discovered item")
    source_url: str = Field(..., description="Original source URL")
    speaker: str = Field(..., description="Primary speaker associated with the content")
    content_type: str = Field(..., description="Content type suggested by discovery")


class DiscoveryRequest(BaseModel):
    """Input parameters for the discovery stage."""
    speaker: str = Field(..., description="Speaker to discover content for")
    start_date: str = Field(..., description="Start of discovery date range (YYYY-MM-DD)")
    end_date: str = Field(..., description="End of discovery date range (YYYY-MM-DD)")
    search_urls: List[str] = Field(default_factory=list, description="URLs to search for speaker content")


class DiscoveryContext(BaseModel):
    """Processing context for discovery operation."""
    speaker: str = Field(..., description="Speaker to discover content for")
    start_date: str = Field(..., description="Start of discovery date range (YYYY-MM-DD)")
    end_date: str = Field(..., description="End of discovery date range (YYYY-MM-DD)")
    search_urls: List[str] = Field(..., description="URLs to search for speaker content")
    run_timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),
        description="Timestamp for this discovery run"
    )


class DiscoveryData(BaseModel):
    """Discovery operation data."""
    discovery_id: str = Field(..., description="Unique identifier for this discovery run")
    discovered_articles: List[DiscoveredArticle] = Field(default_factory=list, description="List of discovered articles")
    speaker: str = Field(..., description="Speaker for whom content was discovered")
    date_range: str = Field(..., description="Date range for discovery")
    total_found: int = Field(0, description="Total articles found by agent")
    new_articles: int = Field(0, description="New articles added (after deduplication)")
    duplicates_skipped: int = Field(0, description="Duplicate articles skipped")


class DiscoveryResult(BaseModel):
    """Result of discovery operation."""
    success: bool = Field(..., description="Whether discovery was successful")
    data: Optional[DiscoveryData] = Field(None, description="Discovery data")
    error_message: Optional[str] = Field(None, description="Error message if discovery failed")
