"""Pydantic models for article extraction and navigation."""
from typing import Literal, Optional, Union
from pydantic import BaseModel, Field

DateSource = Literal["datetime_attr", "schema_org", "url_path", "near_title", "metadata"]


class DateCandidate(BaseModel):
    """Date candidate extracted from a specific source."""
    date: str  # YYYY-MM-DD
    source: DateSource


class DateVoteResult(BaseModel):
    """Result of date voting process."""
    publication_date: Optional[str] = Field(None, description="Publication date of the article")
    date_score: Optional[int] = Field(None, description="Score of the article's date")
    date_source: Optional[DateSource] = Field(None, description="Source of the article's date")


class ArticleExtraction(BaseModel):
    """Article data extracted by LLM (before voting)."""
    title: str = Field(..., description="Title of the article")
    url: str = Field(..., description="URL of the article")
    date_candidates: list[DateCandidate] = Field(default_factory=list, description="Date candidates extracted from the article")


class Article(BaseModel):
    """Final article with computed date metadata."""
    title: str = Field(..., description="Title of the article")
    url: str = Field(..., description="URL of the article")
    date_candidates: list[DateCandidate] = Field(default_factory=list, description="Date candidates extracted from the article")
    publication_date: Optional[str] = Field(None, description="Publication date of the article")
    date_score: Optional[int] = Field(None, description="Score of the article's date")
    date_source: Optional[DateSource] = Field(None, description="Source of the article's date")


class NavigationAction(BaseModel):
    """Action for navigating to more content."""
    type: Literal["click", "scroll"]
    value: Optional[str] = Field(None, description="CSS selector for click, not used for scroll")


class PageExtraction(BaseModel):
    """LLM extraction result from a page. Articles are ArticleExtraction before voting, Article after."""
    articles: list[ArticleExtraction | Article] = Field(default_factory=list, description="Articles extracted from the page")
    next_action: Optional[NavigationAction] = Field(None, description="Next action to take")
    extraction_issues: list[str] = Field(default_factory=list, description="Issues with the extraction")
