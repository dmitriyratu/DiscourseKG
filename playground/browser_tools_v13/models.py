"""Pydantic models for article extraction and navigation."""
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field


class DateSource(str, Enum):
    """Date source: .value is the name (for JSON/Pydantic), .description and .weight attached."""
    def __new__(cls, name: str, description: str = "", weight: int = 0):
        obj = str.__new__(cls, name)
        obj._value_ = name
        obj.description = description
        obj.weight = weight
        return obj

    datetime_attr = ("datetime_attr", "<time datetime=\"...\">", 7)
    schema_org = ("schema_org", "schema.org datePublished", 5)
    url_path = ("url_path", "date segment in the URL path (e.g. .../january-28-2026/, .../2026/01/28/)", 3)
    near_title = ("near_title", "date in the article title or on the line immediately above/below the title", 2)
    metadata = ("metadata", "other page metadata", 1)

    @classmethod
    def weight_for(cls, name: str) -> int:
        try:
            return cls(name).weight
        except ValueError:
            return 0

    @classmethod
    def for_prompt(cls) -> tuple[str, str]:
        """(enum_values, bullet_list) for use in prompt assembly."""
        enum = ", ".join(s.value for s in cls)
        bullets = "\n".join(f"- {s.value}: {s.description}" for s in cls)
        return enum, bullets


class DateCandidate(BaseModel):
    """Date candidate extracted from a specific source."""
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    source: DateSource = Field(..., description="Source of the date candidate")


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
