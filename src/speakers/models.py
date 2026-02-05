"""Speaker data models for the DiscourseKG platform."""

from typing import Dict, List, Optional
from enum import Enum
from pydantic import BaseModel, Field


class Industry(str, Enum):
    """Industry/domain classification for speakers."""
    POLITICS = "politics"
    TECHNOLOGY = "technology"
    FINANCE = "finance"
    HEALTHCARE = "healthcare"
    ENERGY = "energy"
    MEDIA = "media"
    ACADEMIA = "academia"


class Speaker(BaseModel):
    """Individual speaker profile."""
    display_name: str = Field(..., description="Full formatted name for display purposes")
    role: str = Field(..., description="Position/title")
    organization: str = Field(..., description="Affiliated organization or institution")
    industry: Industry = Field(..., description="Domain/sector")
    region: str = Field(..., description="Geographic location")
    date_of_birth: str = Field(..., description="Speaker's birth date")
    bio: str = Field(..., description="Biographical information about the speaker")
    search_urls: List[str] = Field(default_factory=list, description="URLs to search for speaker content")


class SpeakerRegistry(BaseModel):
    """Registry of all speakers in the system."""
    speakers: Dict[str, Speaker]

