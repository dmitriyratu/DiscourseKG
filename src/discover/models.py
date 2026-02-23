"""
Pydantic models for the discovery stage.
"""

import hashlib
from typing import List, Optional, Self
from pydantic import BaseModel, Field
from datetime import datetime

from src.discover.agent.models import Article
from src.shared.models import StageOperationResult
from src.utils.string_utils import slugify


class DiscoverStageMetadata(BaseModel):
    """Metadata stored in pipeline state for discover stage."""
    date_score: int = Field(..., description="Confidence score for the date")
    date_source: str = Field(..., description="Source of the date (datetime_attr, url_path, etc.)")


class DiscoveredArticle(BaseModel):
    """Article discovered by the discovery agent."""
    id: str = Field(..., description="Unique identifier (format: title-slug_urlhash)")
    publication_date: str = Field(..., description="Publication date (YYYY-MM-DD)")
    title: str = Field(..., description="Article title")
    url: str = Field(..., description="Article URL")
    search_url: Optional[str] = Field(None, description="Search page URL where article was found")
    date_score: int = Field(..., description="Confidence score for the date")
    date_source: str = Field(..., description="Source of the date (datetime_attr, url_path, etc.)")

    @classmethod
    def generate_id(cls, article: Article) -> str:
        """Generate unique ID from article: {title_slug}_{url_hash}."""
        title_slug = slugify(article.title, max_length=40)
        url_hash = hashlib.md5(article.url.encode()).hexdigest()[:6]
        return f"{title_slug}_{url_hash}"

    @classmethod
    def from_article(cls, article: Article, search_url: Optional[str] = None) -> Self:
        """Create DiscoveredArticle from Article model."""
        return cls(
            id=cls.generate_id(article),
            title=article.title,
            url=article.url,
            publication_date=article.publication_date,
            search_url=search_url,
            date_score=article.date_score,
            date_source=article.date_source.value,
        )


class DiscoveryRequest(BaseModel):
    """Input parameters for the discovery stage."""
    start_date: str = Field(..., description="Start of discovery date range (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End of discovery date range (YYYY-MM-DD); None = today")
    search_urls: List[str] = Field(default_factory=list, description="URLs to search for content")


class DiscoveryContext(BaseModel):
    """Processing context for discovery operation."""
    start_date: str = Field(..., description="Start of discovery date range (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End of discovery date range (YYYY-MM-DD); None = today")
    search_urls: List[str] = Field(..., description="URLs to search for content")
    run_timestamp: str = Field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d_%H:%M:%S"),
        description="Timestamp for this discovery run"
    )


class DiscoveryData(BaseModel):
    """Discovery operation data."""
    discovery_id: str = Field(..., description="Unique identifier for this discovery run")
    discovered_articles: List[DiscoveredArticle] = Field(default_factory=list, description="List of discovered articles")
    date_range: str = Field(..., description="Date range for discovery")
    total_found: int = Field(0, description="Total articles found by agent")
    new_articles: int = Field(0, description="New articles added (after deduplication)")
    duplicates_skipped: int = Field(0, description="Duplicate articles skipped")


class DiscoveryResult(StageOperationResult[DiscoveryData]):
    """Result of discovery operation."""
    pass
