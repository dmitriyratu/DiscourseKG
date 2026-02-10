"""
Pydantic models for the discovery stage.
"""

from typing import List, Optional, Self
from pydantic import BaseModel, Field
from datetime import datetime
from src.shared.models import StageOperationResult
from src.discover.agent.models import Article

class DiscoverStageMetadata(BaseModel):
    """Metadata stored in pipeline state for discover stage."""
    date_score: int = Field(..., description="Confidence score for the date")
    date_source: str = Field(..., description="Source of the date (datetime_attr, url_path, etc.)")


class DiscoveredArticle(BaseModel):
    """Article discovered by the discovery agent."""
    id: str = Field(..., description="Unique identifier (format: YYYY-MM-DD-title-slug-hash)")
    speaker: str = Field(..., description="Speaker associated with the article")
    publication_date: str = Field(..., description="Publication date (YYYY-MM-DD)")
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    date_score: int = Field(..., description="Confidence score for the date")
    date_source: str = Field(..., description="Source of the date (datetime_attr, url_path, etc.)")
    
    
    @classmethod
    def from_article(cls, article: Article, article_id: str, speaker: str) -> Self:
        """Create DiscoveredArticle from Article model."""
        return cls(
            id=article_id,
            title=article.title,
            url=article.url,
            publication_date=article.publication_date,
            date_score=article.date_score,
            date_source=article.date_source.value,
            speaker=speaker
        )


class DiscoveryRequest(BaseModel):
    """Input parameters for the discovery stage."""
    speaker: str = Field(..., description="Speaker to discover content for")
    start_date: str = Field(..., description="Start of discovery date range (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End of discovery date range (YYYY-MM-DD); None = today")
    search_urls: List[str] = Field(default_factory=list, description="URLs to search for speaker content")


class DiscoveryContext(BaseModel):
    """Processing context for discovery operation."""
    speaker: str = Field(..., description="Speaker to discover content for")
    start_date: str = Field(..., description="Start of discovery date range (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End of discovery date range (YYYY-MM-DD); None = today")
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


class DiscoveryResult(StageOperationResult[DiscoveryData]):
    """Result of discovery operation."""
    pass
