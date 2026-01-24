"""Pydantic models for article extraction and navigation."""
from typing import Literal
from pydantic import BaseModel


class Article(BaseModel):
    """Extracted article with publication date metadata."""
    title: str
    url: str
    publication_date: str | None = None
    date_confidence: Literal["HIGH", "MEDIUM", "LOW", "NONE"]
    date_source: Literal["datetime_attr", "schema_org", "url_path", "near_title", "metadata"]


class NavigationAction(BaseModel):
    """Action for navigating to more content."""
    type: Literal["click"]
    value: str  # CSS selector for click


class PageExtraction(BaseModel):
    """LLM extraction result from a page."""
    articles: list[Article] = []
    next_action: NavigationAction | None = None
    extraction_issues: list[str] = []
